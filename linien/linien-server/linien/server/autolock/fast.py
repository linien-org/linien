# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

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
            round((shift * (-1)) * self.parameters.sweep_amplitude.value * 8191)
        )

        print("lock point is", lock_point, shift)

        self.parameters.autolock_target_position.value = int(lock_point)
        self.parameters.autolock_preparing.value = False
        self.control.exposed_write_registers()
        self.control.exposed_start_lock()

        self._done = True

    def after_lock(self):
        pass
