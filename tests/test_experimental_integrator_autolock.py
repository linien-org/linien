import math
import numpy as np
from matplotlib import pyplot as plt
from migen import (
    Signal,
    Module,
    Instance,
    ClockSignal,
    ResetSignal,
    Array,
    Record,
    ClockDomain,
    ClockDomainsRenamer,
    If,
    bits_for,
)
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus


TARGET_IDXS = (328, 350)
DEFAULT_SCALE_FACTOR = 0.5
COND_LT = 0
COND_GT = 1

LENGHT_TOLERANCE_FACTOR = 0.5


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(noise_level):
    x = np.linspace(-30, 30, 512)
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return central_peak + smaller_peaks + (np.random.randn(len(x)) * noise_level)


def add_noise(spectrum, level=100):
    return spectrum + (np.random.randn(len(spectrum)) * level)


def get_xscale(spectrum, target_idxs):
    part = spectrum[target_idxs[0] : target_idxs[1]]

    return np.abs(np.argmin(part) - np.argmax(part))


def sum_up(spectrum):
    sum_ = 0
    summed = []

    for idx, value in enumerate(spectrum):
        summed.append(sum_ + value)
        sum_ += value

    return summed


def sum_at_xscale(summed, xscale):
    new = []

    for idx, value in enumerate(summed):
        if idx < xscale:
            old = 0
        else:
            old = summed[idx - xscale]

        new.append(value - old)

    return new


def sign(value):
    return 1 if value >= 1 else -1


def get_left_peak(summed_xscaled, target_idxs):
    selected_region = summed_xscaled[target_idxs[0] : target_idxs[1]]
    # in the selected region, we may have 1 minimum and one maximum
    # we know that we are interested in the "left" extremum --> sort extrema
    # by index and take the first one
    extremum = np.min([np.argmin(selected_region), np.argmax(selected_region)])
    current_idx = target_idxs[0] + extremum
    return current_idx


def get_peaks(summed_xscaled, target_idxs):
    current_idx = get_left_peak(summed_xscaled, target_idxs)

    peaks = []

    peaks.append(summed_xscaled[current_idx])
    yscale = np.abs(peaks[-1])

    while True:
        if current_idx == 0:
            break
        current_idx -= 1

        value = summed_xscaled[current_idx]
        last_peak = peaks[-1]

        if sign(last_peak) == sign(value):
            if np.abs(value) > np.abs(last_peak):
                peaks[-1] = value
        else:
            peaks.append(value)

    return peaks


def get_lock_position_from_description(spectrum, description):
    description_idx = 0

    print(description)

    for idx, value in enumerate(spectrum):
        current_threshold = description[description_idx]

        if sign(value) == sign(current_threshold) and abs(value) >= abs(
            current_threshold
        ):
            description_idx += 1

            if description_idx == len(description):
                # this was the last peak!
                return idx

    plt.clf()
    plt.plot(spectrum)
    plt.show()
    raise Exception("not found")


def test_get_description():
    spectrum = spectrum_for_testing(0)

    initial_spectra = []
    for idx in range(10):
        initial_spectra.append(add_noise(spectrum))

    xscales = []
    for initial_spectrum in initial_spectra:
        xscales.append(get_xscale(initial_spectrum, TARGET_IDXS))
    xscale = int(round(np.mean(xscales)))
    print(xscale)

    all_peaks = []

    for initial_spectrum in initial_spectra:
        plt.plot(initial_spectrum, label="initial")
        summed = sum_up(initial_spectrum)
        summed_xscaled = sum_at_xscale(summed, xscale)
        # plt.plot(summed, label="summed")
        plt.plot([_ / xscale for _ in summed_xscaled], label="summed_xscaled / xscale")

        peaks = get_peaks(summed_xscaled, TARGET_IDXS)
        all_peaks.append(peaks)

    first_peaks = [peaks[0] for peaks in all_peaks]
    first_peak_mean = np.mean(first_peaks)
    first_peak_std = np.std(first_peaks)

    # TODO: Think about it. sigma=2 should be 95 % confidence. Handle the case that the difference two lines below is negative
    sigma_factor = 4

    noise_level = first_peak_std * sigma_factor
    print("NOISE", noise_level)

    description = [
        # FIXME: take care that (1-XXX) is never negative (or even < .5)
        peak * (1 - abs(noise_level / peak))
        for peak in all_peaks[0]
    ]
    description = [peak for peak in description if abs(peak) > abs(noise_level)]
    description = list(reversed(description))

    # now find out how much we have to wait in the end (because we detect the peak
    # too early because our threshold is too low)
    last_peak_description_height = description[-1]
    initial_spectrum = initial_spectra[0]
    summed = sum_up(initial_spectrum)
    summed_xscaled = sum_at_xscale(summed, xscale)
    real_peak_idx = get_left_peak(summed_xscaled, TARGET_IDXS)
    current_idx = real_peak_idx
    while True:
        current_idx -= 1
        if np.abs(summed_xscaled[current_idx]) < np.abs(last_peak_description_height):
            break
    final_wait_time = real_peak_idx - current_idx
    print("FINAL", final_wait_time)

    print(np.array(description) / xscale)

    lock_positions = []
    for initial_spectrum in initial_spectra:
        summed = sum_up(initial_spectrum)
        summed_xscaled = sum_at_xscale(summed, xscale)

        lock_positions.append(
            get_lock_position_from_description(summed_xscaled, description)
            + final_wait_time
        )

        plt.axvline(lock_positions[-1])
        break

    plt.axvspan(TARGET_IDXS[0], TARGET_IDXS[1], alpha=0.2, color="red")

    plt.legend()
    plt.show()


if __name__ == "__main__":
    test_get_description()
