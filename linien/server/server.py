import os
import sys

sys.path += ["../../"]
import rpyc
import click
import _thread
import pickle
import numpy as np

from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import AuthenticationError
from random import random

from autolock.autolock import Autolock
from parameters import Parameters

from linien.config import DEFAULT_SERVER_PORT
from linien.common import (
    check_plot_data,
    update_control_signal_history,
    N_POINTS,
    pack,
    unpack,
)
from linien.server.parameter_store import ParameterStore
from linien.server.optimization.optimization import OptimizeSpectroscopy
from linien.server.pid_optimization.pid_optimization import (
    PIDOptimization,
    PSDAcquisition,
)


class BaseService(rpyc.Service):
    """A service that provides functionality for seamless integration of
    parameter access on the client."""

    def __init__(self):
        self.parameters = Parameters()
        self.parameter_store = ParameterStore(self.parameters)
        self._uuid_mapping = {}

    def on_connect(self, client):
        self._uuid_mapping[client] = client.root.uuid

    def on_disconnect(self, client):
        uuid = self._uuid_mapping[client]
        self.parameters.unregister_remote_listeners(uuid)

    def exposed_get_param(self, param_name):
        return pack(self.parameters._get_param(param_name).value)

    def exposed_set_param(self, param_name, value):
        self.parameters._get_param(param_name).value = unpack(value)

    def exposed_init_parameter_sync(self, uuid):
        return self.parameters.init_parameter_sync(uuid)

    def exposed_register_remote_listener(self, uuid, param_name):
        return self.parameters.register_remote_listener(uuid, param_name)

    def exposed_register_remote_listeners(self, uuid, param_names):
        for param_name in param_names:
            self.exposed_register_remote_listener(uuid, param_name)

    def exposed_get_listener_queue(self, uuid):
        return self.parameters.get_listener_queue(uuid)


class RedPitayaControlService(BaseService):
    """Control server that runs on the RP that provides high-level methods."""

    def __init__(self, **kwargs):
        self._cached_data = {}
        self.exposed_is_locked = None

        super().__init__()

        from registers import Registers

        self.registers = Registers(**kwargs)
        self.registers.connect(self, self.parameters)

    def run_acquiry_loop(self):
        """Starts a background process that keeps polling control and error
        signal. Every received value is pushed to `parameters.to_plot`."""

        def data_received(is_raw, plot_data, data_uuid):
            # When a parameter is changed, `pause_acquisition` is set.
            # This means that the we should skip new data until we are sure that
            # it was recorded with the new settings.
            if not self.parameters.pause_acquisition.value:
                if data_uuid != self.data_uuid:
                    return

                data_loaded = pickle.loads(plot_data)

                if not is_raw:
                    is_locked = self.parameters.lock.value

                    if not check_plot_data(is_locked, data_loaded):
                        print(
                            "warning: incorrect data received for lock state, ignoring!"
                        )
                        return

                    self.parameters.to_plot.value = plot_data

                    self.parameters.control_signal_history.value = (
                        update_control_signal_history(
                            self.parameters.control_signal_history.value,
                            data_loaded,
                            is_locked,
                            self.parameters.control_signal_history_length.value,
                        )
                    )
                else:
                    self.parameters.acquisition_raw_data.value = plot_data

        self.registers.run_data_acquisition(data_received)
        self.pause_acquisition()
        self.continue_acquisition()

    def exposed_write_data(self):
        """Syncs the parameters with the FPGA registers."""
        self.registers.write_registers()

    def task_running(self):
        return (
            self.parameters.autolock_running.value
            or self.parameters.optimization_running.value
            or self.parameters.psd_acquisition_running.value
            or self.parameters.psd_optimization_running.value
        )

    def exposed_start_autolock(self, x0, x1, spectrum, additional_spectra=None):
        spectrum = pickle.loads(spectrum)
        #start_watching = self.parameters.watch_lock.value
        start_watching = False
        auto_offset = self.parameters.autolock_determine_offset.value

        if not self.task_running():
            autolock = Autolock(self, self.parameters)
            self.parameters.task.value = autolock
            autolock.run(
                x0,
                x1,
                spectrum,
                should_watch_lock=start_watching,
                auto_offset=auto_offset,
                additional_spectra=pickle.loads(additional_spectra)
                if additional_spectra is not None
                else None,
            )

    def exposed_start_optimization(self, x0, x1, spectrum):
        if not self.task_running():
            optim = OptimizeSpectroscopy(self, self.parameters)
            self.parameters.task.value = optim
            optim.run(x0, x1, spectrum)

    def exposed_start_psd_acquisition(self):
        if not self.task_running():
            self.parameters.task.value = PSDAcquisition(self, self.parameters)
            self.parameters.task.value.run()

    def exposed_start_pid_optimization(self):
        if not self.task_running():
            self.parameters.task.value = PIDOptimization(self, self.parameters)
            self.parameters.task.value.run()

    def exposed_start_ramp(self):
        self.pause_acquisition()

        self.parameters.combined_offset.value = 0
        self.parameters.lock.value = False
        self.exposed_write_data()

        self.continue_acquisition()

    def exposed_start_lock(self):
        self.pause_acquisition()

        self.parameters.lock.value = True
        self.exposed_write_data()

        self.continue_acquisition()

    def exposed_shutdown(self):
        """Kills the server."""
        self.registers.acquisition.shutdown()
        _thread.interrupt_main()
        # we use SystemExit instead of os._exit because we want to call atexit
        # handlers
        raise SystemExit

    def exposed_get_server_version(self):
        import linien

        return linien.__version__

    def exposed_get_restorable_parameters(self):
        return self.parameters._restorable_parameters

    def exposed_pause_acquisition(self):
        self.pause_acquisition()

    def exposed_continue_acquisition(self):
        self.continue_acquisition()

    def exposed_set_csr_direct(self, k, v):
        """Directly sets a CSR register. This method is intended for debugging.
        Normally, the FPGA should be controlled via manipulation of parameters."""
        self.registers.set(k, v)

    def pause_acquisition(self):
        """Pause continuous acquisition. Call this before changing a parameter
        that alters the error / control signal. This way, no inconsistent signals
        reach the application. After setting the new parameter values, call
        `continue_acquisition`."""
        self.parameters.pause_acquisition.value = True
        self.data_uuid = random()
        self.registers.acquisition.pause_acquisition()

    def continue_acquisition(self):
        """Continue acquisition after a short delay, when we are sure that the
        new parameters values have been written to the FPGA and that data that
        is now recorded is recorded with the correct parameters."""
        self.parameters.pause_acquisition.value = False
        self.registers.acquisition.continue_acquisition(self.data_uuid)


class FakeRedPitayaControl(BaseService):
    def __init__(self):
        super().__init__()
        self.exposed_is_locked = None

    def exposed_write_data(self):
        pass

    def run_acquiry_loop(self):
        import threading
        from time import sleep
        from random import randint

        def run():
            while True:
                max_ = randint(0, 8191)
                gen = lambda: np.array([randint(-max_, max_) for _ in range(N_POINTS)])
                self.parameters.to_plot.value = pickle.dumps(
                    {
                        "error_signal_1": gen(),
                        "error_signal_1_quadrature": gen(),
                        "error_signal_2": gen(),
                        "error_signal_2_quadrature": gen(),
                    }
                )
                sleep(0.1)

        t = threading.Thread(target=run)
        t.daemon = True
        t.start()

    def exposed_shutdown(self):
        _thread.interrupt_main()
        os._exit(0)

    def exposed_start_autolock(self, x0, x1, spectrum):
        print("start autolock", x0, x1)

    def exposed_start_optimization(self, x0, x1, spectrum):
        print("start optimization")
        self.parameters.optimization_running.value = True

    def exposed_get_restorable_parameters(self):
        return self.parameters._restorable_parameters

    def exposed_get_server_version(self):
        import linien

        return linien.__version__

    def pause_acquisition(self):
        pass

    def continue_acquisition(self):
        pass


@click.command()
@click.argument("port", default=DEFAULT_SERVER_PORT, type=int, required=False)
@click.option(
    "--fake", is_flag=True, help="Runs a fake server that just returns random data"
)
@click.option(
    "--remote-rp",
    help="Allows to run the server locally for development and "
    "connects to a RedPitaya. Specify the RP's credentials "
    "as follows: "
    "--remote-rp=root:myPassword@rp-f0xxxx.local",
)
def run_server(port, fake=False, remote_rp=False):
    print("start server at port", port)

    if fake:
        print("starting fake server")
        control = FakeRedPitayaControl()
    else:
        if remote_rp is not None:
            assert (
                "@" in remote_rp and ":" in remote_rp
            ), "invalid format, should be root:myPassword@rp-f0xxxx.local"

            username, tmp = remote_rp.split(":", 1)
            r_host, r_password = "".join(reversed(tmp)).split("@", 1)
            host = "".join(reversed(r_host))
            password = "".join(reversed(r_password))
            control = RedPitayaControlService(
                host=host, user=username, password=password
            )
        else:
            control = RedPitayaControlService()

    control.run_acquiry_loop()
    control.exposed_write_data()

    failed_auth_counter = {"c": 0}

    def username_and_password_authenticator(sock):
        # when a client starts the server, it supplies this hash via an environment
        # variable
        secret = os.environ.get("LINIEN_AUTH_HASH")

        # client always sends auth hash, even if we run in non-auth mode
        # --> always read 64 bytes, otherwise rpyc connection can't be established
        received = sock.recv(64)

        # as a protection against brute force, we don't accept requests after
        # too many failed auth requests
        if failed_auth_counter["c"] > 1000:
            print("received too many failed auth requests!")
            sys.exit(1)

        if secret is None:
            print("warning: no authentication set up")
        else:

            if received != secret.encode():
                print("received invalid credentials: ", received)

                failed_auth_counter["c"] += 1

                raise AuthenticationError("invalid username / password")

            print("authentication successful")

        return sock, None

    t = ThreadedServer(
        control, port=port, authenticator=username_and_password_authenticator
    )
    t.start()


if __name__ == "__main__":
    run_server()
