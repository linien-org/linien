import cma
import numpy as np
from linien.common import MHz, Vpp
from linien.server.parameters import Parameters
from linien.server.optimization.engine import MultiDimensionalOptimizationEngine, OptimizerEngine


def test_multi():
    e = MultiDimensionalOptimizationEngine(
        [
            [0, 10],
            [0, 10]
        ]
    )

    while not e.finished():
        solution = e.ask()
        result = cma.ff.rosen(solution)
        e.tell(result, solution)

    print('done', e.es.result_pretty())


class FakeControl:
    def __init__(self, parameters: Parameters):
        self.parameters = parameters

    def pause_acquisition(self):
        pass

    def continue_acquisition(self):
        pass

    def exposed_write_data(self):
        print(f'write: freq={self.parameters.modulation_frequency.value / MHz} amp={self.parameters.modulation_amplitude.value / Vpp}')


def test_optimization():
    params = Parameters()
    control = FakeControl(params)


    # check that 0D optimization doesn't really optimize
    params.optimization_mod_freq_enabled.value = False
    params.optimization_mod_amp_enabled.value = False
    engine = OptimizerEngine(control, params)
    assert engine.finished()


    # test 2D optimization
    params.optimization_mod_freq_enabled.value = True
    params.optimization_mod_amp_enabled.value = True
    engine = OptimizerEngine(control, params)
    assert not engine.finished()


    def generate_slope(N=1024, slope=1):
        return np.array([v * slope for v in range(N)])

    idx = 0
    iq_phase = 48

    while not engine.finished():
        engine.request_and_set_new_parameters()

        f = params.modulation_frequency.value / MHz
        a = params.modulation_amplitude.value / Vpp

        fitness = (5**2 - (f-5)**2) + (2**2 - (a-0.5)**2)

        generated_slope = generate_slope(slope=fitness)
        i = np.cos(iq_phase / 360 * 2 * np.pi) * generated_slope
        q = np.sin(iq_phase / 360 * 2 * np.pi) * generated_slope
        engine.tell(i, q)

        idx += 1
        if idx == 100:
            break

    engine.use_best_parameters()
    assert params.modulation_amplitude.value / Vpp - .5 < 0.1
    assert params.modulation_frequency.value / MHz - 5 < 0.1
    demod_phase = params.demodulation_phase_a.value
    assert abs(demod_phase - iq_phase) < .1 or (abs(demod_phase - 180 - iq_phase)) < .1


if __name__ == '__main__':
    test_multi()
    test_optimization()