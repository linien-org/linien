from linien.common import (
    AUTO_DETECT_AUTOLOCK_MODE,
    FAST_AUTOLOCK,
    N_POINTS,
    ROBUST_AUTOLOCK,
    determine_shift_by_correlation,
)


class AutolockAlgorithmSelector:
    """This class helps deciding which autolock method should be used."""

    def __init__(
        self,
        mode_preference,
        spectrum,
        additional_spectra,
        line_width,
        N_spectra_required=3,
    ):
        self.done = False
        self.mode = None
        self.spectra = [spectrum] + (additional_spectra or [])
        self.N_spectra_required = N_spectra_required
        self.line_width = line_width

        if mode_preference != AUTO_DETECT_AUTOLOCK_MODE:
            self.mode = mode_preference
            self.done = True
            return

        self.check()

    def handle_new_spectrum(self, spectrum):
        self.spectra.append(spectrum)
        self.check()

    def check(self):
        if self.done:
            return True

        if len(self.spectra) < self.N_spectra_required:
            return
        else:
            ref = self.spectra[0]
            additional = self.spectra[1:]
            abs_shifts = [
                abs(determine_shift_by_correlation(1, ref, spectrum)[0] * N_POINTS)
                for spectrum in additional
            ]
            max_shift = max(abs_shifts)
            print("jitter / line width ratio:", max_shift / (self.line_width / 2))

            if max_shift <= self.line_width / 2:
                self.mode = FAST_AUTOLOCK
            else:
                self.mode = ROBUST_AUTOLOCK

            self.done = True
