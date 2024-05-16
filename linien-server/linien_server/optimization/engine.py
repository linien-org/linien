# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

import math
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import cma

import logging

from linien_common.common import MHz, Vpp
from linien_server.optimization.utils import (
    FINAL_ZOOM_FACTOR,
    get_max_slope,
    optimize_phase_from_iq,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NoOptimizationEngine:
    def __init__(self, *args):
        pass

    def finished(self):
        return True

    def ask(self):
        raise NotImplementedError()

    def tell(self, *args):
        raise NotImplementedError()


class OneDimensionalOptimizationEngine:
    def __init__(self, bounds):
        bounds = list(bounds)
        bounds.append([0.0, 1.0])
        self._multi = MultiDimensionalOptimizationEngine(bounds)
        self._last_additional_param = 0.5

    def ask(self):
        params = self._multi.ask()
        self._last_additional_param = params[1]
        return [params[0]]

    def finished(self):
        return self._multi.finished()

    def tell(self, fitness, parameters):
        parameters = list(parameters)
        parameters.append(self._last_additional_param)
        self._multi.tell(fitness, parameters)


class MultiDimensionalOptimizationEngine:
    def __init__(self, bounds, x0=None):
        self.bounds = bounds

        if x0 is not None:
            x0_converted = self.params_to_internal(x0)
        else:
            x0_converted = [0.5 for v in bounds]

        self.es = cma.CMAEvolutionStrategy(
            x0_converted,
            0.5,
            {"bounds": [[0 for v in bounds], [1 for v in bounds]]},
        )

        self._pending = []
        self._done = []
        self._results = []

    def params_to_internal(self, parameters):
        new_parameters = []
        for [min_, max_], param in zip(self.bounds, parameters):
            new_parameters.append((param - min_) / (max_ - min_))
        return new_parameters

    def internal_to_params(self, internal):
        parameters = []
        for [min_, max_], param in zip(self.bounds, internal):
            parameters.append((param * (max_ - min_)) + min_)
        return parameters

    def finished(self):
        return self.es.stop()

    def ask(self):
        if not self._pending:
            self._pending = self.es.ask()

        return self.internal_to_params(self._pending.pop())

    def tell(self, fitness, parameters):
        self._results.append(fitness)
        self._done.append(parameters)

        if not self._pending:
            self.es.tell(
                [self.params_to_internal(p) for p in self._done], self._results
            )
            self._results = []
            self._done = []


class OptimizerEngine:
    def __init__(self, control, params):
        self.control = control
        self.parameters = params

        self.init_opt_with_bounds()

        self.all_params = [
            params.modulation_frequency,
            params.modulation_amplitude,
            self.get_demod_phase_param(),
        ]
        self.params_before_start = [p.value for p in self.all_params]

        self.parameters.optimization_optimized_parameters.value = (
            self.params_before_start
        )

        self.initial_slope = None
        self.last_parameters = None
        self.last_parameters_internal = None

    def init_opt_with_bounds(self):
        params = self.parameters

        self.to_optimize = []
        self.bounds = []

        if params.optimization_mod_freq_enabled.value:
            self.to_optimize.append(params.modulation_frequency)
            freqs = list(
                sorted(
                    [
                        params.optimization_mod_freq_min.value * MHz,
                        params.optimization_mod_freq_max.value * MHz,
                    ]
                )
            )
            self.bounds.append(freqs)

        if params.optimization_mod_amp_enabled.value:
            self.to_optimize.append(params.modulation_amplitude)
            ampls = list(
                sorted(
                    [
                        params.optimization_mod_amp_min.value * Vpp,
                        params.optimization_mod_amp_max.value * Vpp,
                    ]
                )
            )
            self.bounds.append(ampls)

        self.opt = [
            NoOptimizationEngine,
            OneDimensionalOptimizationEngine,
            MultiDimensionalOptimizationEngine,
        ][len(self.bounds)]([[0, 1]] * len(self.bounds))

    def request_and_set_new_parameters(self, use_initial_parameters=False):
        self.control.exposed_pause_acquisition()

        if use_initial_parameters:
            for param, initial in zip(self.all_params, self.params_before_start):
                param.value = initial
        else:
            new_params = self.opt.ask()
            new_params_converted = [
                self.bounds[idx][0] + p * (self.bounds[idx][1] - self.bounds[idx][0])
                for idx, p in enumerate(new_params)
            ]

            for param, value in zip(self.to_optimize, new_params_converted):
                param.value = value

            self.last_parameters = list(new_params_converted)
            self.last_parameters_internal = list(new_params)

        self.control.exposed_write_registers()
        self.control.exposed_continue_acquisition()

    def finished(self):
        return self.opt.finished()

    def get_demod_phase_param(self):
        params = self.parameters
        dual_channel = params.dual_channel.value
        channel = params.optimization_channel.value

        return (
            self.parameters.demodulation_phase_a,
            self.parameters.demodulation_phase_b,
        )[0 if not dual_channel else (0, 1)[channel]]

    def tell(self, i, q):
        if self.initial_slope is None:
            self.initial_slope = get_max_slope(i, FINAL_ZOOM_FACTOR)

        optimized_phase, optimized_slope = optimize_phase_from_iq(
            i, q, FINAL_ZOOM_FACTOR
        )
        old_phase_value = self.get_demod_phase_param().value
        new_phase_value = old_phase_value - optimized_phase
        if new_phase_value > 360:
            new_phase_value -= 360
        if new_phase_value < 0:
            new_phase_value = 360 - abs(new_phase_value)

        improvement = (optimized_slope - self.initial_slope) / self.initial_slope
        params = self.parameters
        if improvement > 0 and improvement > params.optimization_improvement.value:
            params.optimization_improvement.value = improvement
            complete_parameter_set = self.params_before_start[:]
            complete_parameter_set[2] = new_phase_value

            if self.last_parameters:
                for param, value in zip(self.to_optimize, self.last_parameters):
                    idx = {
                        self.parameters.modulation_frequency: 0,
                        self.parameters.modulation_amplitude: 1,
                    }[param]
                    complete_parameter_set[idx] = value

            params.optimization_optimized_parameters.value = complete_parameter_set

        logger.debug(f"improvement {improvement * 100}")

        fitness = math.log(1 / optimized_slope)

        if self.last_parameters_internal is not None:
            self.opt.tell(fitness, self.last_parameters_internal)

    def use_best_parameters(self):
        optimized = self.parameters.optimization_optimized_parameters.value

        for param, value in zip(self.all_params, optimized):
            param.value = value
