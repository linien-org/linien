# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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

import numpy as np
from linien_common.common import N_POINTS, AutolockMode, determine_shift_by_correlation

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

N_SPECTRA_REQUIRED = 3


class AutolockAlgorithmSelector:
    """This class helps deciding which autolock method should be used."""

    def __init__(
        self,
        mode_preference: AutolockMode,
        spectrum: np.ndarray,
        additional_spectra: list[np.ndarray] | None,
        line_width: int,
    ) -> None:
        self.done = False
        self.mode = None
        self.spectra = [spectrum] + (additional_spectra or [])
        self.line_width = line_width

        if mode_preference != AutolockMode.AUTO_DETECT:
            self.mode = mode_preference
            self.done = True
        else:
            self.check()

    def handle_new_spectrum(self, spectrum: np.ndarray) -> None:
        self.spectra.append(spectrum)
        self.check()

    def check(self) -> None:
        if not self.done and len(self.spectra) > N_SPECTRA_REQUIRED:
            abs_shifts = []
            for spectrum in self.spectra[1:]:
                shift, _, _ = determine_shift_by_correlation(
                    1, self.spectra[0], spectrum
                )
                abs_shifts.append(abs(shift * N_POINTS))
            max_shift = max(abs_shifts)
            logger.debug(
                f"jitter / line width ratio: {max_shift / (self.line_width / 2)}"
            )
            if max_shift <= self.line_width / 2:
                self.mode = AutolockMode.SIMPLE
            else:
                self.mode = AutolockMode.ROBUST
            self.done = True
