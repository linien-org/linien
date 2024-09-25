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

from linien_common.common import (
    SpectrumUncorrelatedException,
    determine_shift_by_correlation,
)
from linien_common.communication import LinienControlService

logger = logging.getLogger(__name__)


class SimpleAutolock:
    """Spectroscopy autolock based on correlation."""

    def __init__(
        self,
        control: LinienControlService,
        parameters,
        first_error_signal,
        first_error_signal_rolled,
        x0,
        x1,
        additional_spectra=None,
    ) -> None:
        self.control = control
        self.parameters = parameters

        self.first_error_signal_rolled = first_error_signal_rolled

        self._done = False
        self._error_counter = 0

    def handle_new_spectrum(self, spectrum) -> None:
        if self._done:
            return

        try:
            shift, zoomed_ref, zoomed_err = determine_shift_by_correlation(
                1, self.first_error_signal_rolled, spectrum
            )
        except SpectrumUncorrelatedException:
            self._error_counter += 1
            logger.warning("Skipping spectrum because it is not correlated.")
            if self._error_counter > 10:
                raise
            return

        target_position = int(
            round((shift * (-1)) * self.parameters.sweep_amplitude.value * 8191)
        )
        logger.debug(f"Target position is {target_position}, shift is {shift}.")
        self.control.exposed_write_registers()
        self.control.exposed_pause_acquisition()
        logger.info("Start lock.")
        self.parameters.lock.value = True
        self.exposed_write_registers()
        self.exposed_continue_acquisition()
        self._done = True

    def after_lock(self):
        pass
