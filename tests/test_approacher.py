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

import numpy as np
from linien_common.common import get_lock_point
from linien_server.optimization.approach_line import Approacher
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


def test_approacher(plt):
    def _get_signal(shift):
        return get_signal(
            parameters.sweep_amplitude.value, parameters.sweep_center.value, shift
        )

    for ref_shift in (-0.4, -0.2, 0.3):
        for target_shift in (-0.3, 0.6):
            print(f"----- ref_shift={ref_shift}, target_shift={target_shift} -----")
            parameters = Parameters()
            control = FakeControl(parameters)

            # approaching a line at the center is too easy
            # we generate a reference signal that is shifted in some direction
            # and then simulate that the user wants to approach a line that is not at
            # the center (this is done using get_lock_point)
            reference_signal = _get_signal(ref_shift)

            (
                central_y,
                target_slope_rising,
                _,
                rolled_reference_signal,
                line_width,
                peak_idxs,
            ) = get_lock_point(reference_signal, 0, len(reference_signal))

            plt.plot(reference_signal)
            plt.plot(rolled_reference_signal)

            assert abs(central_y - Y_SHIFT) < 1

            approacher = Approacher(
                control,
                parameters,
                rolled_reference_signal,
                100,
                central_y,
                wait_time_between_current_corrections=0,
            )

            found = False
            rng = np.random.default_rng(seed=0)
            for _ in range(100):
                shift = target_shift * (1 + (0.025 * rng.standard_normal()))
                error_signal = _get_signal(shift)[:]
                approacher.approach_line(error_signal)

                if parameters.sweep_amplitude.value <= 0.2:
                    found = True
                    break

            assert found
            assert abs((-1 * target_shift) - parameters.sweep_center.value) < 0.1
            print("found!")


if __name__ == "__main__":
    test_approacher()
