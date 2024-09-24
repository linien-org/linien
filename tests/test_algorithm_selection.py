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
from linien_server.autolock.robust import RobustAutolock
from linien_server.autolock.simple import SimpleAutolock
from linien_server.server import FakeRedPitayaControlService

Y_SHIFT = 4000
N_POINTS = 16384
LOW_JITTER = 10 / 8191
HIGH_JITTER = 1000 / 8191


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


def test_forced_algorithm_selection():
    reference_signal = get_signal(1, 0, shift=0)
    center = int(N_POINTS / 2)
    x0 = int(center - (0.01 * N_POINTS))
    x1 = int(center + (0.01 * N_POINTS))
    next_signal = get_signal(1, 0, shift=0.1)

    for mode_preference in (AutolockMode.SIMPLE, AutolockMode.ROBUST):
        control = FakeRedPitayaControlService()
        parameters = control.parameters
        parameters.autolock_mode_preference.value = mode_preference
        autolock = Autolock(control, parameters)
        autolock.run(x0, x1, reference_signal, auto_offset=True)

        parameters.to_plot.value = pickle.dumps(
            {"error_signal_1": next_signal, "error_signal_2": []}
        )

        assert autolock.algorithm_selector.mode == mode_preference
        assert parameters.autolock_mode.value == mode_preference

        if mode_preference == AutolockMode.SIMPLE:
            assert isinstance(autolock.algorithm, SimpleAutolock)
        else:
            assert isinstance(autolock.algorithm, RobustAutolock)


def test_automatic_algorithm_selection():

    reference_signal = get_signal(1, 0, shift=0)
    center = int(N_POINTS / 2)
    x0 = int(center - (0.01 * N_POINTS))
    x1 = int(center + (0.01 * N_POINTS))
    reference_signal = get_signal(1, 0, shift=0)

    for jitter in (LOW_JITTER, HIGH_JITTER):
        control = FakeRedPitayaControlService()
        parameters = control.parameters
        parameters.autolock_mode_preference.value = AutolockMode.AUTO_DETECT

        autolock = Autolock(control, parameters)
        autolock.run(x0, x1, reference_signal, auto_offset=True)

        assert autolock.algorithm_selector.mode == AutolockMode.AUTO_DETECT

        next_signal = get_signal(1, 0, jitter)[:]

        for next_signal in 10 * [get_signal(1, 0, jitter)[:]]:
            parameters.to_plot.value = pickle.dumps(
                {"error_signal_1": next_signal, "error_signal_2": []}
            )

        if jitter == LOW_JITTER:
            assert autolock.algorithm_selector.mode == AutolockMode.SIMPLE
            assert parameters.autolock_mode.value == AutolockMode.SIMPLE
            assert isinstance(autolock.algorithm, SimpleAutolock)
        else:
            assert autolock.algorithm_selector.mode == AutolockMode.ROBUST
            assert parameters.autolock_mode.value == AutolockMode.ROBUST
            assert isinstance(autolock.algorithm, RobustAutolock)


if __name__ == "__main__":
    test_automatic_algorithm_selection()
    test_forced_algorithm_selection()
