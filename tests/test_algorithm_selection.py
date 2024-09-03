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
from linien_server.autolock.robust import RobustAutolock
from linien_server.autolock.simple import SimpleAutolock
from linien_server.server import FakeRedPitayaControlService

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


def test_forced_algorithm_selection():
    def _get_signal(shift):
        return get_signal(1, 0, shift)

    for forced in (AutolockMode.SIMPLE, AutolockMode.ROBUST):
        control = FakeRedPitayaControlService()
        parameters = control.parameters
        parameters.autolock_mode_preference.value = forced

        reference_signal = _get_signal(0)
        autolock = Autolock(control, parameters)

        ref_shift = 0
        N = len(reference_signal)
        new_center_point = int((N / 2) - ((ref_shift / 2) * N))

        autolock.run(
            int(new_center_point - (0.01 * N)),
            int(new_center_point + (0.01 * N)),
            reference_signal,
            auto_offset=True,
        )

        assert autolock.algorithm_selector.select() == forced
        assert parameters.autolock_mode.value == forced

        if forced == AutolockMode.SIMPLE:
            assert isinstance(autolock.algorithm, SimpleAutolock)
        else:
            assert isinstance(autolock.algorithm, RobustAutolock)


def test_automatic_algorithm_selection():
    def _get_signal(shift):
        return get_signal(1, 0, shift)

    LOW_JITTER = 10 / 8191
    HIGH_JITTER = 1000 / 8191
    for jitter in (LOW_JITTER, HIGH_JITTER):
        print(f"jitter {jitter}")
        control = FakeRedPitayaControlService()
        parameters = control.parameters
        parameters.autolock_mode_preference.value = AutolockMode.AUTO_DETECT

        reference_signal = _get_signal(0)
        autolock = Autolock(control, parameters)

        ref_shift = 0
        N = len(reference_signal)
        new_center_point = int((N / 2) - ((ref_shift / 2) * N))

        autolock.run(
            int(new_center_point - (0.01 * N)),
            int(new_center_point + (0.01 * N)),
            reference_signal,
            auto_offset=True,
        )

        assert autolock.algorithm_selector.select() == AutolockMode.AUTO_DETECT

        for _ in range(10):
            error_signal = _get_signal(jitter)[:]
            parameters.to_plot.value = pickle.dumps(
                {"error_signal_1": error_signal, "error_signal_2": []}
            )

        if jitter == LOW_JITTER:
            assert autolock.algorithm_selector.select() == AutolockMode.SIMPLE
            assert parameters.autolock_mode.value == AutolockMode.SIMPLE
            assert isinstance(autolock.algorithm, SimpleAutolock)
        else:
            assert autolock.algorithm_selector.select() == AutolockMode.ROBUST
            assert parameters.autolock_mode.value == AutolockMode.ROBUST
            assert isinstance(autolock.algorithm, RobustAutolock)


if __name__ == "__main__":
    test_automatic_algorithm_selection()
    test_forced_algorithm_selection()
