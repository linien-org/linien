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
from linien_common.enums import AutolockMode
from linien_server.autolock.autolock import Autolock
from linien_server.server import FakeRedPitayaControlService

Y_SHIFT = 4000
N_POINTS = 16384


def get_signal(sweep_amplitude, center, shift):

    def spectrum_for_testing(x):
        def peak(x):
            return np.exp(-np.abs(x)) * np.sin(x)

        central_peak = peak(x) * 2048
        smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
        return central_peak + smaller_peaks + Y_SHIFT

    max_val = np.pi * 5 * sweep_amplitude
    new_center = center + shift
    x = np.linspace((-1 + new_center) * max_val, (1 + new_center) * max_val, N_POINTS)
    return spectrum_for_testing(x)


def test_autolock():
    for ref_shift in (0, -0.7, 0.3):
        for target_shift in (0.5, -0.3, 0.6):

            control = FakeRedPitayaControlService()
            parameters = control.parameters
            parameters.autolock_mode_preference.value = AutolockMode.SIMPLE
            autolock = Autolock(control, parameters)

            reference_signal = get_signal(1, 0, ref_shift)
            error_signal = get_signal(1, 0, target_shift)

            N = len(reference_signal)
            new_center_point = int((N / 2) - ((ref_shift / 2) * N))

            autolock.run(
                int(new_center_point - (0.01 * N)),
                int(new_center_point + (0.01 * N)),
                reference_signal,
            )

            parameters.to_plot.value = pickle.dumps(
                {"error_signal_1": error_signal, "error_signal_2": []}
            )

            assert control.parameters.lock.value

            lock_position = parameters.autolock_target_position.value

            ideal_lock_position = (
                -1 * target_shift * parameters.sweep_amplitude.value * 8191
            )
            assert abs(lock_position - ideal_lock_position) <= 15


if __name__ == "__main__":
    test_autolock()
