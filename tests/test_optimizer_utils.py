import numpy as np
from linien.server.optimization.utils import calculate_spectrum_from_iq, get_max_slope, optimize_phase_from_iq
from matplotlib import pyplot as plt
from scipy.optimize import minimize_scalar
from random import randint, random


def test_get_max_slope():
    def generate_slope(N=1024, slope=1):
        return [v * slope for v in range(N)]

    def join(arrays):
        joined = []
        for array in arrays:
            offset = joined[0] if joined else 0
            joined += [v+offset for v in array]
        return joined

    i = generate_slope()

    assert get_max_slope(
        i, 10
    ) == 1

    i = join([
        generate_slope(slope=1),
        generate_slope(slope=-2),
        generate_slope(slope=1)
    ])
    q = i

    assert get_max_slope(
        i, 10
    ) == 2.0


def test_iq():
    Y_SHIFT = 0

    def peak(x):
        return np.exp(-np.abs(x)) * np.sin(x)

    def spectrum_for_testing(x):
        central_peak = (peak(x) * 2048)
        return central_peak + Y_SHIFT

    def get_sin(phase=0):
        points_per_sin = 100
        shift = phase / 360 * 2 * np.pi
        return np.sin(
            np.linspace(
                0 + shift,
                points_per_sin * 2 * np.pi + shift,
                10000
            )
        )

    def generate_fake_data(spectrum, phase=0):
        data = np.array([])

        sin = get_sin(phase=phase)

        for point in spectrum:
            data = np.append(data, point * sin)

        return data

    def demod(data, phase=0):
        sin = get_sin(phase=phase)

        block_size = len(sin)
        N_points = round(len(data) / block_size)

        demodulated_data = []

        for N in range(N_points):
            data_slice = data[N * block_size:(N+1)*block_size]
            demodulated = np.mean(
                sin * data_slice
            )
            demodulated_data.append(demodulated)

        return demodulated_data

    final_zoom_factor = 10

    ramp_amplitude = 1.0
    max_val = np.pi * 5 * ramp_amplitude
    x = np.linspace(-1 * max_val, 1 * max_val, 100)

    for iteration in range(1):
        spectrum = spectrum_for_testing(x) * 2
        data = generate_fake_data(spectrum, phase=30)#phase=randint(0, 360))

        spectrum2 = spectrum_for_testing(x + random() * 3)
        data2 = generate_fake_data(spectrum2, phase=randint(0, 360))

        spectrum3 = spectrum_for_testing(x + random() * 3)
        data3 = generate_fake_data(spectrum3, phase=randint(0, 360))

        combined = data# + data2 + data3

        def get_slope(signal):
            return get_max_slope(
                signal, final_zoom_factor
            )

        min_result = minimize_scalar(
            lambda phase: -1 * get_slope(demod(combined, phase=phase)),
            method='Bounded',
            bounds=(0, 360)
        )


        i = demod(combined)
        q = demod(combined, phase=90)

        optimized_phase, optimized_slope = optimize_phase_from_iq(i, q, final_zoom_factor)

        assert abs(min_result.x - optimized_phase) <= .1
        assert abs(abs(min_result.fun) - optimized_slope) / optimized_slope <= .001


if __name__ == '__main__':
    test_get_max_slope()
    test_iq()