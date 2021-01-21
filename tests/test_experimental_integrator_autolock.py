import numpy as np
from matplotlib import pyplot as plt
from scipy.signal import correlate, resample


TARGET_IDXS = (328, 350)


class LockPositionNotFound(Exception):
    pass


class UnableToFindDescription(Exception):
    pass


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(noise_level):
    x = np.linspace(-30, 30, 512)
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return central_peak + smaller_peaks + (np.random.randn(len(x)) * noise_level)


def add_noise(spectrum, level):
    return spectrum + (np.random.randn(len(spectrum)) * level)


def add_jitter(spectrum, level):
    shift = int(round(np.random.randn() * level))
    print("shift", shift)
    return np.roll(spectrum, shift)


def get_lock_region(spectrum, target_idxs):
    part = spectrum[target_idxs[0] : target_idxs[1]]
    return tuple(
        sorted([target_idxs[0] + np.argmin(part), target_idxs[0] + np.argmax(part)])
    )


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


def get_lock_position_from_description(
    spectrum, description, x_scale, initial_spectrum
):
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
            # TODO: this .9 factor is very arbitrary. also: first peak should have special treatment bc of horizontal jitter
            and idx - last_peak_idx > (peak_position - previous_peak_position) * 0.9
        ):
            description_idx += 1
            last_peak_idx = idx
            previous_peak_position = peak_position

            if description_idx == len(description):
                # this was the last peak!
                return idx

    """plt.clf()
    # plt.plot(spectrum, color="blue", alpha=0.5)
    plt.plot(
        get_diff_at_x_scale(sum_up_spectrum(spectrum), x_scale),
        color="green",
        alpha=0.5,
        label="to test",
    )
    # plt.plot(initial_spectrum, color="red", alpha=0.5)
    plt.plot(
        get_diff_at_x_scale(sum_up_spectrum(initial_spectrum), x_scale),
        color="orange",
        alpha=0.5,
        label="initial",
    )

    plt.legend()
    plt.grid()
    plt.show()"""
    raise LockPositionNotFound()


def get_description(spectra, target_idxs):
    # FIXME: TODO: y shift such that initial line always has + and - peak. Is this really needed?
    x_scale = int(
        round(np.mean([get_x_scale(spectrum, target_idxs) for spectrum in spectra]))
    )
    print(f"x scale is {x_scale}")
    for tolerance_factor in [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]:
        print("TOLERANCE", tolerance_factor)
        prepared_spectrum = get_diff_at_x_scale(sum_up_spectrum(spectra[0]), x_scale)
        peaks = get_all_peaks(prepared_spectrum, target_idxs)

        y_scale = peaks[0][1]
        description = [
            (peak_position, peak_height * tolerance_factor)
            for peak_position, peak_height in peaks
        ]
        # it is important to do the filtering that happens here after the previous
        # line as the previous line shrinks the values
        description = [
            (peak_position, peak_height)
            for peak_position, peak_height in description
            if abs(peak_height) > abs(y_scale * (1 - tolerance_factor))
        ]

        # now find out how much we have to wait in the end (because we detect the peak
        # too early because our threshold is too low)
        target_peak_described_height = description[0][1]
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

        # test whether description works fine for every recorded spectrum
        does_work = True
        for spectrum in spectra:
            lock_region = get_lock_region(spectrum, target_idxs)

            try:
                lock_position = (
                    get_lock_position_from_description(
                        spectrum,
                        list(reversed(description)),
                        x_scale,
                        spectra[0],
                    )
                    + final_wait_time
                )
                if not lock_region[0] <= lock_position <= lock_region[1]:
                    raise LockPositionNotFound()

            except LockPositionNotFound:
                does_work = False

        if does_work:
            break
    else:
        raise UnableToFindDescription()

    return list(reversed(description)), final_wait_time, x_scale


def test_get_description():
    spectrum = spectrum_for_testing(0)

    spectra_with_jitter = [
        add_jitter(add_noise(spectrum, 100), 100 if _ > 0 else 0) for _ in range(10)
    ]
    spectra = []

    for idx, spectrum in enumerate(spectra_with_jitter):
        if idx == 0:
            shift = 0
        else:
            shift = np.argmax(correlate(spectra[0], spectrum))
            print("detected", -1 * (shift - len(spectrum)))
        spectra.append(np.roll(spectrum, shift))
        # plt.plot(spectra[-1])

    # plt.show()
    # asd
    description, final_wait_time, x_scale = get_description(spectra, TARGET_IDXS)

    print("DESCRIPTION", description)

    lock_positions = []

    for spectrum in spectra:
        lock_positions.append(
            get_lock_position_from_description(
                spectrum, description, x_scale, spectra[0]
            )
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
