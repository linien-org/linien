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

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import cma

import numpy as np
from linien_common.common import MHz, Vpp
from linien_server.optimization.engine import (
    MultiDimensionalOptimizationEngine,
    OptimizerEngine,
)
from linien_server.parameters import Parameters


def test_multi():
    e = MultiDimensionalOptimizationEngine([[0, 10], [0, 10]])

    while not e.finished():
        solution = e.ask()
        result = cma.ff.rosen(solution)
        e.tell(result, solution)

    print("done", e.es.result_pretty())


class FakeControl:
    def __init__(self, parameters: Parameters):
        self.parameters = parameters

    def exposed_pause_acquisition(self):
        pass

    def exposed_continue_acquisition(self):
        pass

    def exposed_write_registers(self):
        print(
            "write: freq={} amp={}".format(
                self.parameters.modulation_frequency.value / MHz,
                self.parameters.modulation_amplitude.value / Vpp,
            )
        )


def test_optimization():
    params = Parameters()
    control = FakeControl(params)

    def generate_slope(N=1024, slope=1):
        return np.array([v * slope for v in range(N)])

    # # # -------------------------------------------------------
    #  check that 0D optimization only optimizes phase
    # # #-------------------------------------------------------
    params = Parameters()
    control = FakeControl(params)

    params.optimization_mod_freq_enabled.value = False
    params.optimization_mod_amp_enabled.value = False

    engine = OptimizerEngine(control, params)

    iq_phase = 23
    generated_slope = generate_slope(slope=456)
    i = np.cos(iq_phase / 360 * 2 * np.pi) * generated_slope
    q = np.sin(iq_phase / 360 * 2 * np.pi) * generated_slope
    engine.tell(i, q)

    assert engine.finished()
    engine.use_best_parameters()

    # check that demodulation phase was correctly optimized
    demod_phase = params.demodulation_phase_a.value
    assert (
        abs(demod_phase - iq_phase) < 0.1 or (abs(180 - demod_phase - iq_phase)) < 0.1
    )

    # # # -------------------------------------------------------
    # test 1D optimization
    # # # -------------------------------------------------------
    params = Parameters()
    control = FakeControl(params)

    params.optimization_mod_freq_enabled.value = False
    params.optimization_mod_amp_enabled.value = True

    engine = OptimizerEngine(control, params)
    assert not engine.finished()

    idx = 0
    iq_phase = 76

    while not engine.finished():
        engine.request_and_set_new_parameters()

        f = params.modulation_frequency.value / MHz
        a = params.modulation_amplitude.value / Vpp

        fitness = 2**2 - (a - 0.5) ** 2

        generated_slope = generate_slope(slope=fitness)
        i = np.cos(iq_phase / 360 * 2 * np.pi) * generated_slope
        q = np.sin(iq_phase / 360 * 2 * np.pi) * generated_slope
        engine.tell(i, q)

        idx += 1
        if idx == 1000:
            raise Exception("did not finish!")

    engine.use_best_parameters()
    assert params.modulation_amplitude.value / Vpp - 0.5 < 0.1
    # assert params.modulation_frequency.value / MHz - 5 < 0.1
    demod_phase = params.demodulation_phase_a.value
    assert (
        abs(demod_phase - iq_phase) < 0.1 or (abs(180 - demod_phase - iq_phase)) < 0.1
    )

    # # # -------------------------------------------------------
    # test 2D optimization
    # # # -------------------------------------------------------

    params = Parameters()
    control = FakeControl(params)

    params.optimization_mod_freq_enabled.value = True
    params.optimization_mod_amp_enabled.value = True

    engine = OptimizerEngine(control, params)
    assert not engine.finished()

    idx = 0
    iq_phase = 48

    while not engine.finished():
        engine.request_and_set_new_parameters()

        f = params.modulation_frequency.value / MHz
        a = params.modulation_amplitude.value / Vpp

        fitness = (5**2 - (f - 5) ** 2) + (2**2 - (a - 0.5) ** 2)

        generated_slope = generate_slope(slope=fitness)
        i = np.cos(iq_phase / 360 * 2 * np.pi) * generated_slope
        q = np.sin(iq_phase / 360 * 2 * np.pi) * generated_slope
        engine.tell(i, q)

        idx += 1
        if idx == 1000:
            raise Exception("did not finish!")

    engine.use_best_parameters()
    assert params.modulation_amplitude.value / Vpp - 0.5 < 0.1
    assert params.modulation_frequency.value / MHz - 5 < 0.1
    demod_phase = params.demodulation_phase_a.value
    assert (
        abs(demod_phase - iq_phase) < 0.1 or (abs(180 - demod_phase - iq_phase)) < 0.1
    )


if __name__ == "__main__":
    test_multi()
    test_optimization()
