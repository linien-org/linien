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
import pickle
from typing import Optional

import numpy as np
from linien_common.common import (
    SpectrumUncorrelatedException,
    check_plot_data,
    combine_error_signal,
    get_lock_point,
)
from linien_common.communication import LinienControlService
from linien_server.autolock.algorithm_selection import AutolockAlgorithmSelector
from linien_server.autolock.robust import RobustAutolock
from linien_server.autolock.simple import SimpleAutolock
from linien_server.parameters import Parameters

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Autolock:
    def __init__(self, control: LinienControlService, parameters: Parameters) -> None:
        self.control = control
        self.parameters = parameters
        self.parameters.autolock_running.value = False
        self.parameters.autolock_retrying.value = False
        self.reset_properties()
        self.algorithm = None

    def reset_properties(self):
        # we check each parameter before setting it because otherwise this may crash the
        # client if called very often (e.g.if the autolock continuously fails)
        if self.parameters.autolock_failed.value:
            self.parameters.autolock_failed.value = False
        if self.parameters.autolock_locked.value:
            self.parameters.autolock_locked.value = False
        if self.parameters.autolock_watching.value:
            self.parameters.autolock_watching.value = False

    def reset_scan(self):
        self.control.exposed_pause_acquisition()
        self.control.exposed_start_sweep()
        self.control.exposed_continue_acquisition()

    def start_autolock(self, mode):
        logger.debug(f"Start autolock with mode {mode}")
        self.parameters.autolock_mode.value = mode

        self.algorithm = [None, RobustAutolock, SimpleAutolock][mode](
            self.control,
            self.parameters,
            self.spectrum,
            self.first_error_signal_rolled,
            self.peak_idxs[0],
            self.peak_idxs[1],
            additional_spectra=self.additional_spectra,
        )

    def stop(self) -> None:
        """Abort any operation."""
        self.parameters.autolock_preparing.value = False
        self.parameters.autolock_percentage.value = 0
        self.parameters.autolock_running.value = False
        self.parameters.autolock_locked.value = False
        self.parameters.autolock_watching.value = False
        self.parameters.fetch_additional_signals.value = True
        self.parameters.to_plot.remove_callback(self.react_to_new_spectrum)
        self.reset_scan()
        self.parameters.task.value = None

    def relock(self):
        """
        Relock the laser using the reference spectrum recorded in the first locking
        approach.
        """
        # we check each parameter before setting it because otherwise this may crash the
        # client if called very often (e.g.if the autolock continuously fails)
        if not self.parameters.autolock_running.value:
            self.parameters.autolock_running.value = True
        if not self.parameters.autolock_retrying.value:
            self.parameters.autolock_retrying.value = True

        self.reset_properties()
        self.reset_scan()

        # add a listener that listens for new spectrum data and consequently tries to
        # relock.
        self.parameters.to_plot.add_callback(self.react_to_new_spectrum)

    def run(
        self,
        x0: float,
        x1: float,
        spectrum: np.ndarray,  # array of int
        auto_offset: bool = True,
        additional_spectra: Optional[list[np.ndarray]] = None,
    ) -> None:
        """Start the autolock."""
        self.parameters.autolock_running.value = True
        self.parameters.autolock_preparing.value = True
        self.parameters.autolock_percentage.value = 0
        self.parameters.fetch_additional_signals.value = False
        self.additional_spectra = additional_spectra or []
        self.spectrum = spectrum

        (
            mean_signal,
            target_slope_rising,
            _,
            self.first_error_signal_rolled,
            self.line_width,
            self.peak_idxs,
        ) = get_lock_point(self.spectrum, int(x0), int(x1))

        self.central_y = int(mean_signal)

        if auto_offset:
            self.control.exposed_pause_acquisition()
            self.parameters.combined_offset.value = -1 * self.central_y
            self.spectrum -= self.central_y
            self.first_error_signal_rolled -= self.central_y
            self.additional_spectra = [
                s - self.central_y for s in self.additional_spectra
            ]
            self.control.exposed_write_registers()
            self.control.exposed_continue_acquisition()

        self.parameters.target_slope_rising.value = target_slope_rising
        self.control.exposed_write_registers()

        try:
            self.autolock_algorithm_selector = AutolockAlgorithmSelector(
                self.parameters.autolock_mode_preference.value,
                self.spectrum,
                additional_spectra,
                self.line_width,
            )

            if self.autolock_algorithm_selector.done:
                self.start_autolock(self.autolock_algorithm_selector.mode)

        except SpectrumUncorrelatedException:
            # This may happen if `additional_spectra` contain uncorrelated data. Then
            # either AutolockAlgorithmSelector or `start_autolock` may raise this
            # exception
            logger.exception("Error while starting autolock")
            self.parameters.autolock_failed.value = True
            self.stop()

        self.parameters.to_plot.add_callback(self.react_to_new_spectrum)

    def react_to_new_spectrum(self, plot_data: bytes) -> None:
        """
        React to new spectrum data.

        If this is executed for the first time, a reference spectrum is recorded.

        If the autolock is approaching the desired line, a correlation function of the
        spectrum with the reference spectrum is calculated and the laser current is
        adapted such that the targeted line is centered.

        After this procedure is done, the real lock is turned on and after some time the
        lock is verified.
        """
        if (
            self.parameters.pause_acquisition.value
            or not self.parameters.autolock_running.value
        ):
            return

        plot_data_unpickled = pickle.loads(plot_data)
        if plot_data_unpickled is None:
            return

        is_locked = self.parameters.lock.value
        if not check_plot_data(is_locked, plot_data_unpickled):
            return

        try:
            if not is_locked:
                combined_error_signal = combine_error_signal(
                    (
                        plot_data_unpickled["error_signal_1"],
                        plot_data_unpickled.get("error_signal_2"),
                    ),
                    self.parameters.dual_channel.value,
                    self.parameters.channel_mixing.value,
                    self.parameters.combined_offset.value,
                )

                if not self.autolock_algorithm_selector.done:
                    self.autolock_algorithm_selector.handle_new_spectrum(
                        combined_error_signal
                    )
                    self.additional_spectra.append(combined_error_signal)

                    if self.autolock_algorithm_selector.done:
                        self.start_autolock(self.autolock_algorithm_selector.mode)
                    else:
                        return

                if self.algorithm is not None:
                    self.algorithm.handle_new_spectrum(combined_error_signal)
                    return

            else:
                logger.debug("After lock")
                self.parameters.autolock_locked.value = True
                self.parameters.to_plot.remove_callback(self.react_to_new_spectrum)
                self.parameters.autolock_running.value = False
                if self.algorithm is not None:
                    self.algorithm.after_lock()

        except Exception:
            logger.exception("Error while handling new spectrum")
            self.parameters.autolock_failed.value = True
            self.stop()
