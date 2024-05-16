# Copyright 2018-2023 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
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

import logging
import pickle
import subprocess
from pathlib import Path
from random import random
from threading import Event, Thread
from time import sleep
from typing import Any, Optional

import numpy as np
from linien_common.common import DECIMATION, MAX_N_POINTS, N_POINTS
from linien_common.config import ACQUISITION_PORT
from linien_server.csr import PythonCSR
from pyrp3.board import RedPitaya  # type: ignore
from pyrp3.instrument import TriggerSource  # type: ignore
from rpyc import Service
from rpyc.utils.server import ThreadedServer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AcquisitionService(Service):
    def __init__(self) -> None:
        super(AcquisitionService, self).__init__()
        stop_nginx()
        flash_fpga()

        self.red_pitaya = RedPitaya()
        self.csr = PythonCSR(self.red_pitaya)
        self.csr_queue: list[tuple[str, int]] = []
        self.csr_iir_queue: list[tuple[str, list[float], list[float]]] = []

        self.data: bytes | None = pickle.dumps(None)
        self.data_was_raw = False
        self.data_hash: float | None = None
        self.data_uuid: float | None = None

        self.locked = False
        self.exposed_set_sweep_speed(9)
        # when self.locked is set to True, this doesn't mean that the lock is really on.
        # It just means that the lock is requested and that the gateware waits until the
        # sweep is at the correct position for the lock. Therefore, when self.locked is
        # set, the acquisition process waits for confirmation from the gateware that the
        # lock is actually running.
        self.confirmed_that_in_lock = False

        self.fetch_additional_signals = True
        self.raw_acquisition_enabled = False
        self.raw_acquisition_decimation = 0

        self.dual_channel = False

        self.stop_event = Event()
        self.pause_event = Event()
        self.skip_next_data_event = Event()

        self.thread = Thread(
            target=self._acquisition_loop,
            args=(
                self.stop_event,
                self.pause_event,
                self.skip_next_data_event,
            ),
            daemon=True,
        )
        self.thread.start()

    def _acquisition_loop(
        self, stop_event: Event, pause_event: Event, skip_next_data_event: Event
    ) -> None:
        while not stop_event.is_set():
            while self.csr_queue:
                key, value = self.csr_queue.pop(0)
                self.csr.set(key, value)

            while self.csr_iir_queue:
                name, b, a = self.csr_iir_queue.pop(0)
                self.csr.set_iir(name, b, a)

            if self.locked and not self.confirmed_that_in_lock:
                self.confirmed_that_in_lock = bool(
                    self.csr.get("logic_autolock_lock_running")
                )
                if not self.confirmed_that_in_lock:
                    sleep(0.05)
                    continue

            if pause_event.is_set():
                sleep(0.05)
                continue

            # check that scope is triggered; copied from
            # https://github.com/RedPitaya/RedPitaya/blob/14cca62dd58f29826ee89f4b28901602f5cdb1d8/api/src/oscilloscope.c#L115  # noqa: E501
            if not (self.red_pitaya.scope.read(0x1 << 2) & 0x4) <= 0:
                sleep(0.05)
                continue

            if self.raw_acquisition_enabled:
                data_raw = self.read_data_raw(
                    0x10000, self.red_pitaya.scope.write_pointer_trigger, MAX_N_POINTS
                )
                is_raw = True
            else:
                data = self.read_data()
                is_raw = False

            if pause_event.is_set():
                # it may seem strange that we check this here a second time. Reason:
                # `read_data` takes some time and if in the mean time acquisition
                # was paused, we do not want to send the data
                continue

            if skip_next_data_event.is_set():
                skip_next_data_event.clear()
            else:
                if self.raw_acquisition_enabled:
                    self.data = pickle.dumps(data_raw)
                else:
                    self.data = pickle.dumps(data)
                self.data_was_raw = is_raw
                self.data_hash = random()

            self.program_acquisition_and_rearm()

    def read_data(self) -> dict[str, np.ndarray]:
        signals = []

        channel_offsets = [0x10000]
        if self.fetch_additional_signals or self.locked:
            channel_offsets.append(0x20000)

        for channel_offset in channel_offsets:
            channel_data = self.read_data_raw(
                channel_offset,
                self.red_pitaya.scope.write_pointer_trigger,
                N_POINTS,
            )

            for sub_channel_idx in (0, 1):
                signals.append(channel_data[sub_channel_idx])

        signals_named = {}

        if not self.locked:
            signals_named["error_signal_1"] = signals[0]

            if self.fetch_additional_signals and len(signals) >= 3:
                signals_named["error_signal_1_quadrature"] = signals[2]

            if self.dual_channel:
                signals_named["error_signal_2"] = signals[1]
                if self.fetch_additional_signals and len(signals) >= 3:
                    signals_named["error_signal_2_quadrature"] = signals[3]
            else:
                signals_named["monitor_signal"] = signals[1]

        else:
            signals_named["error_signal"] = signals[0]
            signals_named["control_signal"] = signals[1]

            if not self.dual_channel and len(signals) >= 3:
                signals_named["monitor_signal"] = signals[2]

        slow_out = self.csr.get("logic_slow_value")
        slow_out = slow_out if slow_out <= 8191 else slow_out - 16384
        signals_named["slow_control_signal"] = slow_out

        return signals_named

    def read_data_raw(
        self, offset: int, addr: int, data_length: int
    ) -> tuple[Any, ...]:
        max_data_length = 16383
        if data_length + addr > max_data_length:
            to_read_later = data_length + addr - max_data_length
            data_length -= to_read_later
        else:
            to_read_later = 0

        # raw data contains two signals:
        #   2'h0,adc_b_rd,2'h0,adc_a_rd
        #   i.e.: 2 zero bits, channel b (14 bit), 2 zero bits, channel a (14 bit)
        # .copy() is required, because np.frombuffer returns a readonly array
        raw_data = self.red_pitaya.scope.reads(offset + (4 * addr), data_length).copy()

        # raw_data is an array of 32-bit ints. We cast it to 16 bit --> each original
        # int is split into two ints
        raw_data.dtype = np.int16

        # sign bit is at position 14, but we have 16 bit ints
        raw_data[raw_data >= 2**13] -= 2**14

        # order is such that we have first the signal a then signal b
        signals = tuple(raw_data[signal_idx::2] for signal_idx in (0, 1))

        if to_read_later > 0:
            additional_raw_data = self.read_data_raw(offset, 0, to_read_later)
            signals = tuple(
                np.append(signals[signal_idx], additional_raw_data[signal_idx])
                for signal_idx in (0, 1)
            )

        return signals

    def program_acquisition_and_rearm(self, trigger_delay=16384):
        """Program the acquisition settings and rearm acquisition."""
        if not self.locked:
            target_decimation = 2 ** (self.sweep_speed + int(np.log2(DECIMATION)))

            self.red_pitaya.scope.data_decimation = target_decimation
            self.red_pitaya.scope.trigger_delay = int(trigger_delay / DECIMATION) - 1

        elif self.raw_acquisition_enabled:
            self.red_pitaya.scope.data_decimation = 2**self.raw_acquisition_decimation
            self.red_pitaya.scope.trigger_delay = trigger_delay

        else:
            self.red_pitaya.scope.data_decimation = 1
            self.red_pitaya.scope.trigger_delay = int(trigger_delay / DECIMATION) - 1

        self.red_pitaya.scope.rearm(trigger_source=TriggerSource.ext_posedge)

    def exposed_return_data(self, last_hash: Optional[float]) -> tuple[
        bool,
        float | None,
        bool | None,
        bytes | None,
        float | None,
    ]:
        no_data_available = self.data_hash is None
        data_not_changed = self.data_hash == last_hash
        if data_not_changed or no_data_available or self.pause_event.is_set():
            return False, None, None, None, None
        else:
            return True, self.data_hash, self.data_was_raw, self.data, self.data_uuid

    def exposed_set_sweep_speed(self, speed):
        self.sweep_speed = speed
        # if a slow acqisition is currently running and we change the sweep speed we
        # don't want to wait until it finishes
        self.program_acquisition_and_rearm()

    def exposed_set_lock_status(self, locked: bool) -> None:
        self.locked = locked
        self.confirmed_that_in_lock = False

    def exposed_set_fetch_additional_signals(self, fetch: bool) -> None:
        self.fetch_additional_signals = fetch

    def exposed_set_raw_acquisition(self, enabled: bool, decimation: int) -> None:
        self.raw_acquisition_enabled = enabled
        self.raw_acquisition_decimation = decimation

    def exposed_set_dual_channel(self, dual_channel):
        self.dual_channel = dual_channel

    def exposed_set_csr(self, key: str, value: int) -> None:
        self.csr_queue.append((key, value))

    def exposed_set_iir_csr(self, name: str, b: list[float], a: list[float]) -> None:
        self.csr_iir_queue.append((name, b, a))

    def exposed_stop_acquisition(self) -> None:
        self.stop_event.set()
        self.thread.join()
        start_nginx()

    def exposed_pause_acquisition(self):
        self.pause_event.set()
        self.data_hash = None
        self.data = None

    def exposed_continue_acquisition(self, uuid: Optional[float]) -> None:
        self.program_acquisition_and_rearm()
        sleep(0.01)
        # resetting data here is not strictly required but we want to be on the safe
        # side
        self.data_hash = None
        self.data = None
        self.pause_event.clear()
        self.data_uuid = uuid
        # if we are sweeping, we have to skip one data set because an incomplete sweep
        # may have been recorded. When locked, this does not matter
        if self.confirmed_that_in_lock:
            self.skip_next_data_event.clear()
        else:
            self.skip_next_data_event.set()


def flash_fpga():
    filepath = Path(__file__).resolve().parent / "gateware.bin"
    logger.info("Using fpgautil to deploy gateware.")
    subprocess.Popen(["/opt/redpitaya/bin/fpgautil", "-b", str(filepath)]).wait()


def start_nginx():
    subprocess.Popen(["systemctl", "start", "redpitaya_nginx.service"])


def stop_nginx():
    subprocess.Popen(["systemctl", "stop", "redpitaya_nginx.service"]).wait()
    subprocess.Popen(["systemctl", "stop", "redpitaya_scpi.service"]).wait()


if __name__ == "__main__":
    threaded_server = ThreadedServer(AcquisitionService(), port=ACQUISITION_PORT)
    logger.info(f"Starting AcquisitionService on port {ACQUISITION_PORT}")
    threaded_server.start()
