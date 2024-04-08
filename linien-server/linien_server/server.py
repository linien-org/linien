# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

import _thread
import atexit
import logging
import pickle
from copy import copy
from random import randint, random
from socket import socket
from threading import Event, Thread
from time import sleep
from typing import Any, Callable

import numpy as np
import rpyc
from linien_common.common import N_POINTS, check_plot_data, update_signal_history
from linien_common.communication import (
    LinienControlService,
    ParameterValues,
    pack,
    unpack,
)
from linien_common.config import SERVER_PORT
from linien_common.influxdb import InfluxDBCredentials, restore_credentials
from linien_server import __version__
from linien_server.autolock.autolock import Autolock
from linien_server.influxdb import InfluxDBLogger
from linien_server.noise_analysis import PIDOptimization, PSDAcquisition
from linien_server.optimization.optimization import OptimizeSpectroscopy
from linien_server.parameters import Parameters, restore_parameters, save_parameters
from linien_server.registers import Registers
from rpyc.core.protocol import Connection
from rpyc.utils.server import ThreadedServer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseService(rpyc.Service):
    """
    A service that provides functionality for seamless integration of parameter access
    on the client.
    """

    def __init__(self) -> None:
        self.parameters = Parameters()
        self.parameters = restore_parameters(self.parameters)
        atexit.register(save_parameters, self.parameters)
        self._uuid_mapping: dict[Connection, str] = {}

        influxdb_credentials = restore_credentials()
        self.influxdb_logger = InfluxDBLogger(influxdb_credentials, self.parameters)

        self.stop_event = Event()
        self.stop_log_event = Event()

    def on_connect(self, conn: Connection) -> None:
        self._uuid_mapping[conn] = conn.root.uuid

    def on_disconnect(self, conn: Connection) -> None:
        uuid = self._uuid_mapping[conn]
        self.parameters.unregister_remote_listeners(uuid)

    def exposed_get_server_version(self) -> str:
        return __version__

    def exposed_get_param(self, param_name: str) -> bytes | ParameterValues:
        return pack(getattr(self.parameters, param_name).value)

    def exposed_set_param(
        self, param_name: str, value: bytes | ParameterValues
    ) -> None:
        getattr(self.parameters, param_name).value = unpack(value)

    def exposed_reset_param(self, param_name: str) -> None:
        getattr(self.parameters, param_name).reset()

    def exposed_init_parameter_sync(
        self, uuid: str
    ) -> list[tuple[str, Any, bool, bool, bool, bool]]:
        return list(self.parameters.init_parameter_sync(uuid))

    def exposed_register_remote_listener(self, uuid: str, param_name: str) -> None:
        self.parameters.register_remote_listener(uuid, param_name)

    def exposed_register_remote_listeners(
        self, uuid: str, param_names: list[str]
    ) -> None:
        for param_name in param_names:
            self.exposed_register_remote_listener(uuid, param_name)

    def exposed_get_changed_parameters_queue(self, uuid: str) -> list[tuple[str, Any]]:
        return self.parameters.get_changed_parameters_queue(uuid)

    def exposed_set_parameter_log(self, param_name: str, value: bool) -> None:
        if getattr(self.parameters, param_name).log != value:
            logger.debug(f"Setting log for {param_name} to {value}")
            getattr(self.parameters, param_name).log = value

    def exposed_get_parameter_log(self, param_name: str) -> bool:
        return getattr(self.parameters, param_name).log

    def exposed_update_influxdb_credentials(
        self, credentials: InfluxDBCredentials
    ) -> tuple[bool, int, str]:
        credentials = copy(credentials)
        (
            connection_succesful,
            status_code,
            message,
        ) = self.influxdb_logger.test_connection(credentials)
        if connection_succesful:
            self.influxdb_logger.credentials = credentials
            logger.info("InfluxDB credentials updated successfully")
        else:
            logger.info(
                "InfluxDB credentials update failed. Error message: "
                f" {message} (Status Code {status_code})"
            )
        return connection_succesful, status_code, message

    def exposed_get_influxdb_credentials(self) -> InfluxDBCredentials:
        return self.influxdb_logger.credentials

    def exposed_start_logging(self, interval: float) -> None:
        logger.info("Starting logging")
        self.influxdb_logger.start_logging(interval)

    def exposed_stop_logging(self) -> None:
        logger.info("Stopping logging")
        self.influxdb_logger.stop_logging()

    def exposed_get_logging_status(self) -> bool:
        return not self.influxdb_logger.stop_event.is_set()


class RedPitayaControlService(BaseService, LinienControlService):
    """Control server that runs on the RP that provides high-level methods."""

    def __init__(self, host=None):
        self._cached_data = {}
        self.exposed_is_locked = None

        super(RedPitayaControlService, self).__init__()

        self.registers = Registers(control=self, parameters=self.parameters, host=host)
        # Connect the acquisition loop to the parameters: Every received value is pushed
        # to `parameters.to_plot`.
        self.exposed_pause_acquisition()
        self.exposed_continue_acquisition()

        # Start a timer that increases the `ping` parameter once per second. Its purpose
        # is to allow for periodic tasks on the server: just register an `on_change`
        # listener for this parameter.

        self.ping_thread = Thread(
            target=self._send_ping_loop, args=(self.stop_event,), daemon=True
        )
        self.data_pusher_thread = Thread(
            target=self._push_acquired_data_to_parameters,
            args=(self.stop_event,),
            daemon=True,
        )

        self.ping_thread.start()
        self.data_pusher_thread.start()

        self.exposed_write_registers()

    def _send_ping_loop(self, stop_event: Event):
        MAX_PING = 3
        while not stop_event.is_set():
            self.parameters.ping.value += 1
            if self.parameters.ping.value <= MAX_PING:
                logger.debug(f"Ping  {self.parameters.ping.value}")
                if self.parameters.ping.value == MAX_PING:
                    logger.debug("Further pings will be suppressed")
            sleep(1)

    def _push_acquired_data_to_parameters(self, stop_event: Event):
        last_hash = None
        while not stop_event.is_set():
            (
                new_data_returned,
                new_hash,
                data_was_raw,
                new_data,
                data_uuid,
            ) = self.registers.acquisition.exposed_return_data(last_hash)
            if new_data_returned:
                last_hash = new_hash
            # When a parameter is changed, `pause_acquisition` is set. This means that
            # the we should skip new data until we are sure that it was recorded with
            # the new settings.
            if not self.parameters.pause_acquisition.value:
                if data_uuid != self.data_uuid:
                    continue

                data_loaded = pickle.loads(new_data)

                if not data_was_raw:
                    is_locked = self.parameters.lock.value

                    if not check_plot_data(is_locked, data_loaded):
                        logger.error(
                            "incorrect data received for lock state, ignoring!"
                        )
                        continue

                    self.parameters.to_plot.value = new_data

                    # generate signal stats
                    stats = {}
                    for signal_name, signal in data_loaded.items():
                        stats[f"{signal_name}_mean"] = np.mean(signal)
                        stats[f"{signal_name}_std"] = np.std(signal)
                        stats[f"{signal_name}_max"] = np.max(signal)
                        stats[f"{signal_name}_min"] = np.min(signal)
                    self.parameters.signal_stats.value = stats
                    # update signal history (if in locked state)
                    (
                        self.parameters.control_signal_history.value,
                        self.parameters.monitor_signal_history.value,
                    ) = update_signal_history(
                        self.parameters.control_signal_history.value,
                        self.parameters.monitor_signal_history.value,
                        data_loaded,
                        is_locked,
                        self.parameters.control_signal_history_length.value,
                    )
                else:
                    self.parameters.acquisition_raw_data.value = new_data
            sleep(0.05)

    def _task_running(self):
        return (
            self.parameters.autolock_running.value
            or self.parameters.optimization_running.value
            or self.parameters.psd_acquisition_running.value
            or self.parameters.psd_optimization_running.value
        )

    def exposed_write_registers(self) -> None:
        """Sync the parameters with the FPGA registers."""
        self.registers.write_registers()

    def exposed_start_autolock(self, x0, x1, spectrum, additional_spectra=None):
        spectrum = pickle.loads(spectrum)
        # start_watching = self.parameters.watch_lock.value
        start_watching = False
        auto_offset = self.parameters.autolock_determine_offset.value

        if not self._task_running():
            autolock = Autolock(self, self.parameters)
            self.parameters.task.value = autolock
            autolock.run(
                x0,
                x1,
                spectrum,
                should_watch_lock=start_watching,
                auto_offset=auto_offset,
                additional_spectra=(
                    pickle.loads(additional_spectra)
                    if additional_spectra is not None
                    else None
                ),
            )

    def exposed_start_optimization(self, x0, x1, spectrum):
        if not self._task_running():
            optim = OptimizeSpectroscopy(self, self.parameters)
            self.parameters.task.value = optim
            optim.run(x0, x1, spectrum)

    def exposed_start_psd_acquisition(self):
        if not self._task_running():
            self.parameters.task.value = PSDAcquisition(self, self.parameters)
            self.parameters.task.value.run()

    def exposed_start_pid_optimization(self):
        if not self._task_running():
            self.parameters.task.value = PIDOptimization(self, self.parameters)
            self.parameters.task.value.run()

    def exposed_start_sweep(self):
        self.exposed_pause_acquisition()
        self.parameters.combined_offset.value = 0
        self.parameters.lock.value = False
        self.exposed_write_registers()
        self.exposed_continue_acquisition()

    def exposed_start_lock(self):
        self.exposed_pause_acquisition()
        self.parameters.lock.value = True
        self.exposed_write_registers()
        self.exposed_continue_acquisition()

    def exposed_shutdown(self):
        self.stop_event.set()
        self.ping_thread.join()
        self.data_pusher_thread.join()
        self.registers.acquisition.exposed_stop_acquisition()
        # FIXME: hacky way to trigger atexit handlers for saving parameters
        _thread.interrupt_main()
        raise SystemExit()

    def exposed_pause_acquisition(self):
        """
        Pause continuous acquisition. Call this before changing a parameter that alters
        the error / control signal. This way, no inconsistent signals reach the
        application. After setting the new parameter values, call
        `continue_acquisition`.
        """
        self.parameters.pause_acquisition.value = True
        self.data_uuid = random()
        self.registers.acquisition.exposed_pause_acquisition()

    def exposed_continue_acquisition(self):
        """
        Continue acquisition after a short delay, when we are sure that the new
        parameters values have been written to the FPGA and that data that is now
        recorded is recorded with the correct parameters.
        """
        self.parameters.pause_acquisition.value = False
        self.registers.acquisition.exposed_continue_acquisition(self.data_uuid)

    def exposed_set_csr_direct(self, key: str, value: int) -> None:
        """
        Directly sets a CSR register. This method is intended for debugging. Normally,
        the FPGA should be controlled via manipulation of parameters.
        """
        self.registers.set(key, value)


class FakeRedPitayaControlService(BaseService, LinienControlService):
    def __init__(self):
        super().__init__()
        self.exposed_is_locked = None

        self.random_data_thread = Thread(
            target=self._write_random_data_to_parameters_loop,
            args=(self.stop_event,),
            daemon=True,
        )
        self.random_data_thread.start()

    def _write_random_data_to_parameters_loop(self, stop_event: Event):
        while not stop_event.is_set():
            max_ = randint(0, 8191)

            def gen():
                return np.array([randint(-max_, max_) for _ in range(N_POINTS)])

            self.parameters.to_plot.value = pickle.dumps(
                {
                    "error_signal_1": gen(),
                    "error_signal_1_quadrature": gen(),
                    "error_signal_2": gen(),
                    "error_signal_2_quadrature": gen(),
                }
            )
            sleep(0.1)

    def exposed_write_registers(self):
        pass

    def exposed_start_autolock(self, x0, x1, spectrum):
        logger.info(f"Start autolock {x0} {x1}")

    def exposed_start_optimization(self, x0, x1, spectrum):
        logger.info("Start optimization")
        self.parameters.optimization_running.value = True

    def exposed_shutdown(self):
        raise SystemExit()

    def exposed_pause_acquisition(self):
        pass

    def exposed_continue_acquisition(self):
        pass


def run_threaded_server(
    control: BaseService,
    authenticator: Callable[[socket], tuple[socket, None]],
) -> None:
    """Run a (Fake)RedPitayaControlService in a threaded server."""
    if isinstance(control, FakeRedPitayaControlService):
        logger.info("Starting fake server")
    else:
        logger.info("Starting server.")

    thread = ThreadedServer(
        control,
        port=SERVER_PORT,
        authenticator=authenticator,
        protocol_config={"allow_pickle": True, "allow_public_attrs": True},
    )
    thread.start()
