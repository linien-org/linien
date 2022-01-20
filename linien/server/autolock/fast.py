from linien.common import SpectrumUncorrelatedException, determine_shift_by_correlation


class FastAutolock:
    """Spectroscopy autolock based on correlation."""

    def __init__(
        self,
        control,
        parameters,
        first_error_signal,
        first_error_signal_rolled,
        x0,
        x1,
        additional_spectra=None,
    ):
        self.control = control
        self.parameters = parameters

        self.first_error_signal_rolled = first_error_signal_rolled

        self._done = False
        self._error_counter = 0

    def handle_new_spectrum(self, spectrum):
        if self._done:
            return

        try:
            shift, zoomed_ref, zoomed_err = determine_shift_by_correlation(
                1, self.first_error_signal_rolled, spectrum
            )
        except SpectrumUncorrelatedException:
            self._error_counter += 1
            print("skipping spectrum because it is not correlated")

            if self._error_counter > 10:
                raise

            return

        lock_point = int(
            round((shift * (-1)) * self.parameters.ramp_amplitude.value * 8191)
        )

        print("lock point is", lock_point, shift)

        self.parameters.autolock_target_position.value = int(lock_point)
        self.parameters.autolock_preparing.value = False
        self.control.exposed_write_data()
        self.control.exposed_start_lock()

        self._done = True
