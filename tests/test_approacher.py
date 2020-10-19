from ast import Param
import numpy as np
from linien.server.approach_line import Approacher
from linien.server.parameters import Parameter, Parameters
from matplotlib import pyplot as plt


def test_function(x):
    return np.exp(-np.abs(x)) * np.sin(x) * 2048


def get_signal(ramp_amplitude, center, shift):
    max_val = np.pi * 5 * ramp_amplitude
    new_center = center + shift
    x = np.linspace((-1 + new_center) * max_val, (1 + new_center) * max_val, 16384)
    return test_function(x)


class FakeControl:
    def __init__(self, parameters: Parameters):
        self.parameters = parameters

    def pause_acquisition(self):
        pass

    def continue_acquisition(self):
        pass

    def exposed_write_data(self):
        print(f'write: center={self.parameters.center.value} amp={self.parameters.ramp_amplitude.value}')


def test_approacher():
    def _get_signal(shift):
        return get_signal(parameters.ramp_amplitude.value, parameters.center.value, shift)

    parameters = Parameters()
    control = FakeControl(parameters)

    first_error_signal = _get_signal(0)
    approacher = Approacher(
        control,
        parameters,
        first_error_signal,
        100,
        wait_time_between_current_corrections=0)

    found = False
    target_shift = 0.4

    for i in range(100):
        shift = target_shift * (1 + (0.05 * np.random.randn()))
        error_signal = _get_signal(shift)[:]
        approacher.approach_line(error_signal)

        if parameters.ramp_amplitude.value <= 0.2:
            found = True
            break

    assert found
    assert abs((-1 * target_shift) - parameters.center.value) < 0.1

if __name__ == '__main__':
    test_approacher()