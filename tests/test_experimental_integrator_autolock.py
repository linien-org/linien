import numpy as np
from matplotlib import pyplot as plt

TARGET_IDXS = (328, 350)


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(noise_level):
    x = np.linspace(-30, 30, 512)
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return central_peak + smaller_peaks + (np.random.randn(len(x)) * noise_level)


def add_noise(spectrum, level=100):
    return spectrum + (np.random.randn(len(spectrum)) * level)


def get_x_scale(spectrum, target_idxs):
    part = spectrum[target_idxs[0] : target_idxs[1]]
    return np.abs(np.argmin(part) - np.argmax(part))


def sum_up_spectrum(spectrum):
    sum_ = 0
    summed = []

    for value in spectrum:
        summed.append(sum_ + value)
        sum_ += value

    return summed


def get_diff_at_x_scale(summed, xscale):
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


def get_lock_position_from_description(spectrum, description, x_scale):
    summed = sum_up_spectrum(spectrum)
    summed_xscaled = get_diff_at_x_scale(summed, x_scale)

    description_idx = 0
    last_peak_idx = 0
    previous_peak_position = 0

    for idx, value in enumerate(summed_xscaled):
        peak_position, current_threshold = description[description_idx]

        if (
            sign(value) == sign(current_threshold)
            and abs(value) >= abs(current_threshold)
            # TODO: this /2 division is very arbitrary. Probably should be more than / 2 and depend on various things
            #       also: first peak should have special treatment bc of horizontal jitter
            and idx - last_peak_idx > (peak_position - previous_peak_position) * 0.5
        ):
            description_idx += 1
            last_peak_idx = idx
            previous_peak_position = peak_position

            if description_idx == len(description):
                # this was the last peak!
                return idx

    plt.clf()
    plt.plot(spectrum)
    plt.plot(summed_xscaled)
    plt.show()
    raise Exception("not found")


def get_description(spectra, target_idxs):
    x_scale = int(
        round(np.mean([get_x_scale(spectrum, target_idxs) for spectrum in spectra]))
    )
    print(f"x scale is {x_scale}")

    all_peaks = []

    for spectrum in spectra:
        prepared_spectrum = get_diff_at_x_scale(sum_up_spectrum(spectrum), x_scale)
        peaks = get_all_peaks(prepared_spectrum, target_idxs)
        all_peaks.append(peaks)

    target_peaks = [peaks[0][1] for peaks in all_peaks]
    # TODO: Think about it. sigma=2 should be 95 % confidence. Handle the case that the difference two lines below is negative
    sigma_factor = 4
    noise_level = sigma_factor * np.std(target_peaks)

    print(f"noise level is {noise_level}")

    description = [
        # FIXME: take care that (1-XXX) is never negative (or even < .5)
        (peak_position, peak_height * (1 - abs(noise_level / peak_height)))
        for peak_position, peak_height in all_peaks[0]
    ]
    # it is important to do the filtering that happens here after the previous
    # line as the previous line shrinks the values
    description = [
        (peak_position, peak_height)
        for peak_position, peak_height in description
        if abs(peak_height) > abs(noise_level)
    ]

    # now find out how much we have to wait in the end (because we detect the peak
    # too early because our threshold is too low)
    target_peak_described_height = description[0][1]
    initial_spectrum = spectra[0]
    prepared_spectrum = get_diff_at_x_scale(sum_up_spectrum(initial_spectrum), x_scale)
    target_peak_idx = get_target_peak(prepared_spectrum, TARGET_IDXS)
    current_idx = target_peak_idx
    while True:
        current_idx -= 1
        if np.abs(prepared_spectrum[current_idx]) < np.abs(
            target_peak_described_height
        ):
            break
    final_wait_time = target_peak_idx - current_idx
    print(f"final wait time is {final_wait_time} samples")

    return list(reversed(description)), final_wait_time, x_scale


def test_get_description():
    spectrum = spectrum_for_testing(0)

    spectra = [add_noise(spectrum) for _ in range(10)]

    description, final_wait_time, x_scale = get_description(spectra, TARGET_IDXS)

    print("DESCRIPTION", description)

    lock_positions = []

    for spectrum in spectra:
        lock_positions.append(
            get_lock_position_from_description(spectrum, description, x_scale)
            + final_wait_time
        )

        plt.axvline(lock_positions[-1], color="green", alpha=0.5)

    plt.plot(spectra[0])
    # plt.plot(get_diff_at_x_scale(sum_up_spectrum(spectra[0]), x_scale))
    plt.axvspan(TARGET_IDXS[0], TARGET_IDXS[1], alpha=0.2, color="red")

    plt.legend()
    plt.show()


if __name__ == "__main__":
    test_get_description()
