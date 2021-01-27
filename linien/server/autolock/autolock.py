from linien.server.autolock.utils import (
    crop_spectra_to_same_view,
    get_all_peaks,
    get_diff_at_time_scale,
    get_lock_region,
    get_target_peak,
    get_time_scale,
    sign,
    sum_up_spectrum,
)
import numpy as np
from matplotlib import pyplot as plt
from scipy.signal import correlate


FPGA_DELAY_SUMDIFF_CALCULATOR = 2
# FIXME: When programming FPGA, this delay has to be subtracted from final_wait constant
FPGA_DELAY_LOCK_POSITION_FINDER = 3


class LockPositionNotFound(Exception):
    pass


class UnableToFindDescription(Exception):
    pass


def calculate_autolock_instructions(spectra_with_jitter, target_idxs):
    spectra, crop_left = crop_spectra_to_same_view(spectra_with_jitter)

    target_idxs = [idx - crop_left for idx in target_idxs]

    for spectrum in spectra:
        plt.plot(spectrum)
    plt.show()

    # FIXME: TODO: y shift such that initial line always has + and - peak. Is this really needed?
    time_scale = int(
        round(np.mean([get_time_scale(spectrum, target_idxs) for spectrum in spectra]))
    )

    print(f"x scale is {time_scale}")

    for tolerance_factor in [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]:
        print("TOLERANCE", tolerance_factor)
        prepared_spectrum = get_diff_at_time_scale(
            sum_up_spectrum(spectra[0]), time_scale
        )
        peaks = get_all_peaks(prepared_spectrum, target_idxs)

        y_scale = peaks[0][1]
        peaks_filtered = [
            (peak_position, peak_height * tolerance_factor)
            for peak_position, peak_height in peaks
        ]
        # it is important to do the filtering that happens here after the previous
        # line as the previous line shrinks the values
        peaks_filtered = [
            (peak_position, peak_height)
            for peak_position, peak_height in peaks_filtered
            if abs(peak_height) > abs(y_scale * (1 - tolerance_factor))
        ]

        # now find out how much we have to wait in the end (because we detect the peak
        # too early because our threshold is too low)
        target_peak_described_height = peaks_filtered[0][1]
        target_peak_idx = get_target_peak(prepared_spectrum, target_idxs)
        current_idx = target_peak_idx
        while True:
            current_idx -= 1
            if np.abs(prepared_spectrum[current_idx]) < np.abs(
                target_peak_described_height
            ):
                break
        final_wait_time = target_peak_idx - current_idx
        print(f"final wait time is {final_wait_time} samples")

        description = []

        last_peak_position = 0
        for peak_position, peak_height in list(reversed(peaks_filtered)):
            # TODO: this .9 factor is very arbitrary. also: first peak should have special treatment bc of horizontal jitter
            description.append(
                (int(0.9 * (peak_position - last_peak_position)), int(peak_height))
            )
            last_peak_position = peak_position

        # test whether description works fine for every recorded spectrum
        does_work = True
        for spectrum in spectra:
            lock_region = get_lock_region(spectrum, target_idxs)

            try:
                lock_position = (
                    get_lock_position_from_autolock_instructions(
                        spectrum,
                        description,
                        time_scale,
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

    return description, final_wait_time, time_scale


def get_lock_position_from_autolock_instructions(
    spectrum, description, time_scale, initial_spectrum
):
    summed = sum_up_spectrum(spectrum)
    summed_xscaled = get_diff_at_time_scale(summed, time_scale)

    description_idx = 0

    last_detected_peak = 0

    for idx, value in enumerate(summed_xscaled):
        wait_for, current_threshold = description[description_idx]

        if (
            sign(value) == sign(current_threshold)
            and abs(value) >= abs(current_threshold)
            and idx - last_detected_peak > wait_for
        ):
            description_idx += 1
            last_detected_peak = idx

            if description_idx == len(description):
                # this was the last peak!
                return idx

    raise LockPositionNotFound()