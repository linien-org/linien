from linien.common import FAST_AUTOLOCK
import pickle
import numpy as np
from linien.server.autolock.autolock import Autolock
from linien.server.parameters import Parameters
from matplotlib import pyplot as plt

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
            f"write: center={self.parameters.ramp_center.value} amp={self.parameters.ramp_amplitude.value}"
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
            parameters.autolock_mode_preference.value = FAST_AUTOLOCK
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
                -1 * target_shift * parameters.ramp_amplitude.value * 8191
            )
            assert abs(lock_position - ideal_lock_position) <= 15


if __name__ == "__main__":
    test_autolock()
