import numpy as np
from pytest import raises

from linien.common import SpectrumUncorrelatedException, determine_shift_by_correlation

Y_SHIFT = 0


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(x):
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return central_peak + smaller_peaks + Y_SHIFT


def get_signal(ramp_amplitude, center, shift):
    max_val = np.pi * 10 * ramp_amplitude
    new_center = center + shift
    x = np.linspace((-1 + new_center) * max_val, (1 + new_center) * max_val, 2048)
    return spectrum_for_testing(x)


def add_noise(spectrum, level):
    return spectrum + (np.random.randn(len(spectrum)) * level)


def test_determine_shift_by_correlation():
    # check that with good s/n ratio it works
    ref = get_signal(1, 0, 0)
    shifted = np.roll(ref[:], -400)[:]
    determine_shift_by_correlation(1, ref, shifted)

    # check that only noise raises SpectrumUncorrelatedException
    noise_level = 1000
    ref = add_noise(0 * get_signal(1, 0, 0), noise_level)
    second = add_noise(0 * get_signal(1, 0, 0), noise_level)
    with raises(SpectrumUncorrelatedException):
        determine_shift_by_correlation(1, ref, second)[0]

    # check that signal with a lot of noise still does not raise
    # SpectrumUncorrelatedException
    noise_level = 400
    ref = add_noise(get_signal(1, 0, 0), noise_level)
    second = add_noise(get_signal(1, 0, 0), noise_level)
    determine_shift_by_correlation(1, ref, second)[0]

    # check that even more noise results in SpectrumUncorrelated
    noise_level = 1000
    ref = add_noise(get_signal(1, 0, 0), noise_level)
    second = add_noise(get_signal(1, 0, 0), noise_level)
    with raises(SpectrumUncorrelatedException):
        determine_shift_by_correlation(1, ref, second)[0]


if __name__ == "__main__":
    test_determine_shift_by_correlation()
