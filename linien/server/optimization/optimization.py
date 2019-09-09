import math
import pickle
import random
import numpy as np
from time import sleep, time
from scipy.signal import resample

from linien.communication.client import BaseClient
from linien.common import determine_shift_by_correlation, MHz, Vpp

from .cma_es import CMAES


def convert_params(params, xmin, xmax):
    converted = []

    for v, min_, max_ in zip(params, xmin, xmax):
        converted.append(
            min_ + v * (max_ - min_)
        )

    return converted


def get_max_diff(array, interesting_size=200):
    points_mean = interesting_size / 10
    resample_factor = int(len(array) / points_mean)
    filtered = resample(array, resample_factor)

    # resampling assumes periodicity
    # --> if the ends don't match (e.g. doppler background) we have very steep
    # edges. Therefore, we crop them.
    N = int(len(filtered) / 8)
    filtered = filtered[N:-N]

    """plt.plot(filtered)
    plt.plot(np.diff(filtered))
    plt.plot(np.gradient(filtered))
    plt.show()"""
    return np.max(np.abs(np.gradient(filtered)))


def is_centering_iteration(iteration):
    return iteration % 10 == 0 and iteration > 0


class OptimizeSpectroscopy:
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.initial_spectrum = None
        self.iteration = 0

    def run(self, xmin, xmax):
        params = self.parameters

        self.xmin, self.xmax = xmin, xmax

        self.opt = CMAES()
        self.opt.sigma = .5

        self.opt.x0 = [0.5, 0.5, 0.5]
        self.opt._upper_limits = [1, 1, 1]
        self.opt._lower_limits = [0, 0, 0]

        self.fitness_arr = []

        params.to_plot.change(self.react_to_new_spectrum)
        params.optimization_running.value = True
        params.optimization_improvement.value = 0

    def request_new_parameters(self, use_initial_parameters=False):
        new_params = convert_params(self.opt.request_parameter_set(), self.xmin, self.xmax) \
            if not use_initial_parameters \
            else self.initial_params
        self.set_parameters(new_params)

    def react_to_new_spectrum(self, spectrum):
        params = self.parameters

        self.iteration += 1
        spectrum = pickle.loads(spectrum)['error_signal_1']

        if self.initial_spectrum is None:
            params = self.parameters
            self.initial_spectrum = spectrum
            self.initial_params = (
                params.modulation_frequency.value, params.modulation_amplitude.value,
                params.demodulation_phase_a.value
            )
            self.last_parameters = self.initial_params
            self.initial_diff = get_max_diff(spectrum)

        center_line = is_centering_iteration(self.iteration)
        center_line_next_time = is_centering_iteration(self.iteration + 1)

        if self.iteration > 1:
            if center_line:
                # center the line again
                shift, _, _2 = determine_shift_by_correlation(
                    1, self.initial_spectrum, spectrum
                )
                shift *= params.ramp_amplitude.value
                params.center.value -= shift
                self.control.exposed_write_data()
            else:
                max_diff = get_max_diff(spectrum)
                improvement = (max_diff - self.initial_diff) / self.initial_diff
                if improvement > 0 and improvement > params.optimization_improvement.value:
                    params.optimization_improvement.value = improvement

                fitness = math.log(1 / max_diff)
                print('fitness', fitness)

                self.fitness_arr.append(fitness)
                self.opt.insert_fitness_value(fitness, self.last_parameters)

        self.request_new_parameters(use_initial_parameters=center_line_next_time)

    def exposed_stop(self, use_new_parameters):
        if use_new_parameters:
            optimized_parameters = convert_params(
                self.opt.request_results()[0], self.xmin, self.xmax
            )
            self.set_parameters(optimized_parameters)

        self.parameters.optimization_running.value = False
        self.parameters.to_plot.remove_listener(self.react_to_new_spectrum)

    def set_parameters(self, new_params):
        params = self.parameters
        frequency, amplitude, phase = new_params
        print('%.2f MHz, %.2f Vpp, %d deg' % (frequency / MHz, amplitude / Vpp, phase))
        self.control.pause_acquisition()
        params.modulation_frequency.value = frequency
        params.modulation_amplitude.value = amplitude
        params.demodulation_phase_a.value = phase
        self.control.exposed_write_data()
        self.control.continue_acquisition()
        self.last_parameters = new_params
