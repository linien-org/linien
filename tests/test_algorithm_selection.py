from linien.server.autolock.robust import RobustAutolock
from linien.server.autolock.fast import FastAutolock
from linien.common import AUTO_DETECT_AUTOLOCK_MODE, FAST_AUTOLOCK, ROBUST_AUTOLOCK
import pickle
import numpy as np
from linien.server.autolock.autolock import Autolock
from linien.server.parameters import Parameters

Y_SHIFT = 4000


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(x):
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return central_peak + smaller_peaks + Y_SHIFT


def get_signal(ramp_amplitude, center, shift):
    max_val = np.pi * 5 * ramp_amplitude
    new_center = center + shift
    x = np.linspace((-1 + new_center) * max_val, (1 + new_center) * max_val, 16384)
    return spectrum_for_testing(x)


class FakeControl:
    def __init__(self, parameters: Parameters):
        self.parameters = parameters
        self.locked = False

    def pause_acquisition(self):
        pass

    def continue_acquisition(self):
        pass

    def exposed_write_data(self):
        print(
            f"write: center={self.parameters.center.value} amp={self.parameters.ramp_amplitude.value}"
        )

    def exposed_start_lock(self):
        self.locked = True


def test_forced_algorithm_selection():
    def _get_signal(shift):
        return get_signal(1, 0, shift)

    for forced in (FAST_AUTOLOCK, ROBUST_AUTOLOCK):
        parameters = Parameters()
        parameters.autolock_mode_preference.value = forced
        control = FakeControl(parameters)

        reference_signal = _get_signal(0)
        autolock = Autolock(control, parameters)

        ref_shift = 0
        N = len(reference_signal)
        new_center_point = int((N / 2) - ((ref_shift / 2) * N))

        autolock.run(
            int(new_center_point - (0.01 * N)),
            int(new_center_point + (0.01 * N)),
            reference_signal,
            should_watch_lock=True,
            auto_offset=True,
        )

        assert autolock.autolock_mode_detector is not None
        assert autolock.autolock_mode_detector.done

        assert parameters.autolock_mode.value == forced

        if forced == FAST_AUTOLOCK:
            assert isinstance(autolock.algorithm, FastAutolock)
        else:
            assert isinstance(autolock.algorithm, RobustAutolock)


def test_automatic_algorithm_selection():
    def _get_signal(shift):
        return get_signal(1, 0, shift)

    LOW_JITTER = 10 / 8191
    HIGH_JITTER = 1000 / 8191
    for jitter in (LOW_JITTER, HIGH_JITTER):
        print(f"jitter {jitter}")
        parameters = Parameters()
        parameters.autolock_mode_preference.value = AUTO_DETECT_AUTOLOCK_MODE
        control = FakeControl(parameters)

        reference_signal = _get_signal(0)
        autolock = Autolock(control, parameters)

        ref_shift = 0
        N = len(reference_signal)
        new_center_point = int((N / 2) - ((ref_shift / 2) * N))

        autolock.run(
            int(new_center_point - (0.01 * N)),
            int(new_center_point + (0.01 * N)),
            reference_signal,
            should_watch_lock=True,
            auto_offset=True,
        )

        assert autolock.autolock_mode_detector is not None
        assert not autolock.autolock_mode_detector.done
        assert autolock.algorithm is None

        for i in range(10):
            error_signal = _get_signal(jitter)[:]
            parameters.to_plot.value = pickle.dumps(
                {"error_signal_1": error_signal, "error_signal_2": []}
            )

        assert autolock.autolock_mode_detector.done
        if jitter == LOW_JITTER:
            assert parameters.autolock_mode.value == FAST_AUTOLOCK
            assert isinstance(autolock.algorithm, FastAutolock)
        else:
            assert parameters.autolock_mode.value == ROBUST_AUTOLOCK
            assert isinstance(autolock.algorithm, RobustAutolock)


if __name__ == "__main__":
    test_automatic_algorithm_selection()
    test_forced_algorithm_selection()