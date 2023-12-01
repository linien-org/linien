# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
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

import logging

from linien_common.common import N_POINTS, AutolockMode, determine_shift_by_correlation

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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

        if mode_preference != AutolockMode.AUTO_DETECT:
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
            logger.debug(
                "jitter / line width ratio: %s" % (max_shift / (self.line_width / 2))
            )

            if max_shift <= self.line_width / 2:
                self.mode = AutolockMode.SIMPLE
            else:
                self.mode = AutolockMode.ROBUST

            self.done = True
