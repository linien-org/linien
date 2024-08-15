# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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

import pickle

import numpy as np
from linien_common.common import AutolockMode
from linien_server.autolock.autolock import Autolock
from linien_server.parameters import Parameters

Y_SHIFT = 4000


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(x):
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return central_peak + smaller_peaks + Y_SHIFT


def get_signal(sweep_amplitude, center, shift):
    max_val = np.pi * 5 * sweep_amplitude
    new_center = center + shift
    x = np.linspace((-1 + new_center) * max_val, (1 + new_center) * max_val, 16384)
    return spectrum_for_testing(x)


class FakeControl:
    def __init__(self, parameters: Parameters):
        self.parameters = parameters
        self.locked = False

    def exposed_pause_acquisition(self):
        pass

    def exposed_continue_acquisition(self):
        pass

    def exposed_write_registers(self):
        print(
            "write: center={} amp={}".format(
                self.parameters.sweep_center.value,
                self.parameters.sweep_amplitude.value,
            )
        )

    def exposed_start_lock(self):
        self.locked = True


def test_autolock():
    def _get_signal(shift):
        return get_signal(1, 0, shift)

    for ref_shift in (0, -0.7, 0.3):
        for target_shift in (0.5, -0.3, 0.6):
            print(f"----- ref_shift={ref_shift}, target_shift={target_shift} -----")

            parameters = Parameters()
            parameters.autolock_mode_preference.value = AutolockMode.SIMPLE
            control = FakeControl(parameters)

            reference_signal = _get_signal(ref_shift)

            autolock = Autolock(control, parameters)

            N = len(reference_signal)
            new_center_point = int((N / 2) - ((ref_shift / 2) * N))

            autolock.run(
                int(new_center_point - (0.01 * N)),
                int(new_center_point + (0.01 * N)),
                reference_signal,
                should_watch_lock=True,
                auto_offset=True,
            )

            error_signal = _get_signal(target_shift)[:]

            parameters.to_plot.value = pickle.dumps(
                {"error_signal_1": error_signal, "error_signal_2": []}
            )

            assert control.locked

            lock_position = parameters.autolock_target_position.value

            ideal_lock_position = (
                -1 * target_shift * parameters.sweep_amplitude.value * 8191
            )
            assert abs(lock_position - ideal_lock_position) <= 15


if __name__ == "__main__":
    test_autolock()
