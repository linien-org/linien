from linien.common import FAST_AUTOLOCK, ROBUST_AUTOLOCK, determine_shift_by_correlation


class AutolockAlgorithmSelector:
    """This class helps deciding which autolock method should be used."""

    def __init__(self, spectrum, additional_spectra, line_width, N_spectra_required=3):
        self.done = False
        self.mode = None
        self.spectra = [spectrum] + (additional_spectra or [])
        self.N_spectra_required = N_spectra_required
        self.line_width = line_width

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
            shifts = [
                determine_shift_by_correlation(1, ref, spectrum)
                for spectrum in additional
            ]
            max_shift = max(shifts)

            if max_shift <= self.line_width:
                self.mode = FAST_AUTOLOCK
            else:
                self.mode = ROBUST_AUTOLOCK

            self.done = True
