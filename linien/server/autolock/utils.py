import numpy as np
from scipy.signal import correlate


def get_lock_region(spectrum, target_idxs):
    part = spectrum[target_idxs[0] : target_idxs[1]]
    return tuple(
        sorted([target_idxs[0] + np.argmin(part), target_idxs[0] + np.argmax(part)])
    )


def get_time_scale(spectrum, target_idxs):
    part = spectrum[target_idxs[0] : target_idxs[1]]
    return np.abs(np.argmin(part) - np.argmax(part))


def sum_up_spectrum(spectrum):
    sum_ = 0
    summed = []

    for value in spectrum:
        summed.append(sum_ + value)
        sum_ += value

    return summed


def get_diff_at_time_scale(summed, xscale):
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


def get_target_peak(summed_xscaled, target_idxs):
    selected_region = summed_xscaled[target_idxs[0] : target_idxs[1]]
    # in the selected region, we may have 1 minimum and one maximum
    # we know that we are interested in the "left" extremum --> sort extrema
    # by index and take the first one
    extremum = np.min([np.argmin(selected_region), np.argmax(selected_region)])
    current_idx = target_idxs[0] + extremum
    return current_idx


def get_all_peaks(summed_xscaled, target_idxs):
    current_idx = get_target_peak(summed_xscaled, target_idxs)

    peaks = []

    peaks.append((current_idx, summed_xscaled[current_idx]))

    while True:
        if current_idx == 0:
            break
        current_idx -= 1

        value = summed_xscaled[current_idx]
        last_peak_position, last_peak_height = peaks[-1]

        if sign(last_peak_height) == sign(value):
            if np.abs(value) > np.abs(last_peak_height):
                peaks[-1] = (current_idx, value)
        else:
            peaks.append((current_idx, value))

    return peaks


def crop_spectra_to_same_view(spectra_with_jitter):
    cropped_spectra = []

    shifts = []

    for idx, spectrum in enumerate(spectra_with_jitter):
        shift = np.argmax(correlate(spectra_with_jitter[0], spectrum)) - len(spectrum)

        shifts.append(-shift)

    min_shift = min(shifts)
    max_shift = max(shifts)

    length_after_crop = len(spectra_with_jitter[0]) - (max_shift - min_shift)

    for shift, spectrum in zip(shifts, spectra_with_jitter):
        cropped_spectra.append(
            spectrum[shift-min_shift:][:length_after_crop]
        )

    return cropped_spectra, -min_shift + 1