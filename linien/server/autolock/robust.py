from time import time

from linien.common import (
    AUTOLOCK_MAX_N_INSTRUCTIONS,
    SpectrumUncorrelatedException,
    determine_shift_by_correlation,
)
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


class LockPositionNotFound(Exception):
    pass


class UnableToFindDescription(Exception):
    pass


class RobustAutolock:
    def __init__(
        self,
        control,
        parameters,
        first_error_signal,
        first_error_signal_rolled,
        x0,
        x1,
        N_spectra_required=5,
        additional_spectra=None,
    ):
        self.control = control
        self.parameters = parameters

        self.first_error_signal = first_error_signal
        self.x0 = x0
        self.x1 = x1

        self.N_spectra_required = N_spectra_required

        self.spectra = [first_error_signal]

        self._done = False
        self._error_counter = 0

        if additional_spectra is not None:
            # the most recent ones are the ones we are interested in
            additional_spectra = list(reversed(additional_spectra))
            for additional_spectrum in additional_spectra:
                self.handle_new_spectrum(additional_spectrum)

    def handle_new_spectrum(self, spectrum):
        if self._done:
            return

        print("handle new spectrum")
        try:
            determine_shift_by_correlation(1, self.first_error_signal, spectrum)
        except SpectrumUncorrelatedException:
            print("skipping spectrum because it is not correlated")
            self._error_counter += 1
            if self._error_counter > 2:
                raise

            return

        self.spectra.append(spectrum)
        self.parameters.autolock_percentage.value = int(
            round((len(self.spectra) / self.N_spectra_required) * 100)
        )

        if len(self.spectra) == self.N_spectra_required:
            print("enough spectra!, calculate")

            t1 = time()
            description, final_wait_time, time_scale = calculate_autolock_instructions(
                self.spectra, (self.x0, self.x1)
            )
            t2 = time()
            print("calculation of autolock description took", t2 - t1)

            # first reset lock in case it was True. This ensures that autolock
            # starts properly once all parameters are set
            self.parameters.lock.value = False
            self.control.exposed_write_data()

            self.parameters.autolock_time_scale.value = time_scale
            self.parameters.autolock_instructions.value = description
            self.parameters.autolock_final_wait_time.value = final_wait_time

            self.control.exposed_write_data()

            self.parameters.lock.value = True
            self.control.exposed_write_data()

            self.parameters.autolock_preparing.value = False

            self._done = True
        else:
            print(
                "not enough spectra collected: %d of %d"
                % (len(self.spectra), self.N_spectra_required)
            )


def calculate_autolock_instructions(spectra_with_jitter, target_idxs):
    spectra, crop_left = crop_spectra_to_same_view(spectra_with_jitter)

    target_idxs = [idx - crop_left for idx in target_idxs]

    time_scale = int(
        round(np.mean([get_time_scale(spectrum, target_idxs) for spectrum in spectra]))
    )

    print("x scale is %d" % time_scale)

    prepared_spectrum = get_diff_at_time_scale(sum_up_spectrum(spectra[0]), time_scale)
    peaks = get_all_peaks(prepared_spectrum, target_idxs)
    y_scale = peaks[0][1]

    lock_regions = [get_lock_region(spectrum, target_idxs) for spectrum in spectra]

    for tolerance_factor in [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]:
        print("try out tolerance", tolerance_factor)
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
        print("final wait time is %d samples" % final_wait_time)

        description = []

        last_peak_position = 0
        for peak_position, peak_height in list(reversed(peaks_filtered)):
            # TODO: this .9 factor is very arbitrary.
            description.append(
                (int(0.9 * (peak_position - last_peak_position)), int(peak_height))
            )
            last_peak_position = peak_position

        # test whether description works fine for every recorded spectrum
        does_work = True
        for spectrum, lock_region in zip(spectra, lock_regions):
            try:
                lock_position = get_lock_position_from_autolock_instructions(
                    spectrum, description, time_scale, spectra[0], final_wait_time
                )
                if not lock_region[0] <= lock_position <= lock_region[1]:
                    raise LockPositionNotFound()

            except LockPositionNotFound:
                does_work = False

        if does_work:
            break
    else:
        raise UnableToFindDescription()

    if len(description) > AUTOLOCK_MAX_N_INSTRUCTIONS:
        print("warning: autolock description too long. Cropping!", len(description))
        description = description[-AUTOLOCK_MAX_N_INSTRUCTIONS:]

    print("description is", description)
    return description, final_wait_time, time_scale


def get_lock_position_from_autolock_instructions(
    spectrum, description, time_scale, initial_spectrum, final_wait_time
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
                return idx + final_wait_time

    raise LockPositionNotFound()