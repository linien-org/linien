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
from linien_common.common import check_plot_data, combine_error_signal, get_lock_point
from linien_common.communication import LinienControlService
from linien_common.enums import AutolockMode, AutolockStatus
from linien_server.autolock.algorithm_selection import AutolockAlgorithmSelector
from linien_server.autolock.robust import RobustAutolock
from linien_server.autolock.simple import SimpleAutolock
from linien_server.parameters import Parameters

logger = logging.getLogger(__name__)

AUTOLOCK_ALGORITHMS: dict[AutolockMode, type[SimpleAutolock] | type[RobustAutolock]] = {
    AutolockMode.SIMPLE: SimpleAutolock,
    AutolockMode.ROBUST: RobustAutolock,
}


class Autolock:
    algorithm: SimpleAutolock | RobustAutolock | None

    def __init__(self, control: LinienControlService, parameters: Parameters) -> None:
        self.control = control
        self.parameters = parameters
        self.parameters.autolock_status.value = AutolockStatus.STOPPED
        self.algorithm = None

    def stop(self) -> None:
        """Abort any operation."""
        self.parameters.autolock_status.value = AutolockStatus.STOPPED
        self.parameters.fetch_additional_signals.value = True
        self.parameters.to_plot.remove_callback(self.try_to_start_autolock)
        self.control.exposed_start_sweep()
        self.parameters.task.value = None

    def relock(self):
        """
        Relock the laser using the reference spectrum recorded in the first locking
        approach.
        """
        self.parameters.autock_status.value = AutolockStatus.RELOCKING
        self.control.exposed_start_sweep()
        # Add a listener that listens for new spectrum data and tries to relock.
        if self.parameters.autolock_mode_preference == AutolockMode.MANUAL:
            self.start_manual_lock()
        else:
            self.parameters.to_plot.add_callback(self.try_to_start_autolock)

    def run(
        self,
        x0: float = 0,
        x1: float = 0,
        spectrum: np.ndarray = np.array([0]),  # array of int
        additional_spectra: Optional[list[np.ndarray]] = None,
    ) -> None:
        """
        Start the autolock to a lock point between `x0` and `x1` of a `spectrum`.

        An autolock algorithm will be used depending on the `autolock_mode` parameter
        If set `AutolockMode.AUTO_DETECT` an appropriate algorithm will be chosen based
        on the data. If `AutolockMode.MANUAL` is set, `x0`, `x1` and `spectrum` do not
        need to be provided. Instead, the lock will be engaged at the
        `autolock_target_position` parameter and PID control is applied depending on the
        `target_slope_rising` parameter.
        """
        self.parameters.autolock_status.value = AutolockStatus.LOCKING
        self.parameters.fetch_additional_signals.value = False
        self.additional_spectra = additional_spectra or []
        self.spectrum = spectrum

        if self.parameters.autolock_mode_preference.value == AutolockMode.MANUAL:
            self.start_manual_lock()
            return

        (
            mean_signal,
            target_slope_rising,
            _,
            self.first_error_signal_rolled,
            self.line_width,
            self.peak_idxs,
        ) = get_lock_point(self.spectrum, int(x0), int(x1))
        self.central_y = int(mean_signal)

        if self.parameters.autolock_determine_offset.value:
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

        self.algorithm_selector = AutolockAlgorithmSelector(
            self.parameters.autolock_mode_preference.value,
            self.spectrum,
            self.line_width,
            self.additional_spectra,
        )

        self.parameters.to_plot.add_callback(self.try_to_start_autolock)

    def try_to_start_autolock(self, plot_data: bytes) -> None:
        """
        Callback function that handles new plot data, determines an autolock algorithm
        and starts the autolock.
        """
        if (
            self.parameters.pause_acquisition.value
            or self.parameters.autolock_status.value.value != AutolockStatus.LOCKING
        ):
            return

        plot_data_unpickled = pickle.loads(plot_data)
        if plot_data_unpickled is None:
            return

        if not check_plot_data(self.parameters.lock.value, plot_data_unpickled):
            return

        try:
            if not self.parameters.lock.value:
                # prepare the plot data
                combined_error_signal = combine_error_signal(
                    (
                        plot_data_unpickled["error_signal_1"],
                        plot_data_unpickled.get("error_signal_2"),
                    ),
                    self.parameters.dual_channel.value,
                    self.parameters.channel_mixing.value,
                    self.parameters.combined_offset.value,
                )

                if self.algorithm is None:  # algorithm still has to be determined
                    if self.algorithm_selector.mode == AutolockMode.AUTO_DETECT:
                        # feed new data to the algorithm selector
                        self.algorithm_selector.append_spectrum(combined_error_signal)
                        self.additional_spectra.append(combined_error_signal)

                    # If algorithm could be determined with the new data, set the
                    # appropriate algorithm
                    if self.algorithm_selector.mode != AutolockMode.AUTO_DETECT:
                        mode = self.algorithm_selector.mode
                        logger.debug(f"Initialize autolock algorithm (mode {mode})")
                        self.parameters.autolock_mode.value = mode

                        self.algorithm = AUTOLOCK_ALGORITHMS[mode](
                            self.control,
                            self.parameters,
                            self.spectrum,
                            self.first_error_signal_rolled,
                            self.peak_idxs[0],
                            self.peak_idxs[1],
                            additional_spectra=self.additional_spectra,
                        )

                if self.algorithm is not None:  # algorithm was set (with new data)
                    # forward data to the algorithm, will (eventually) engage lock
                    self.algorithm.handle_new_spectrum(combined_error_signal)
            else:  # lock was already engaged
                logger.debug("Autolock finised.")
                self.parameters.autolock_status.value = AutolockStatus.LOCKED
                self.parameters.to_plot.remove_callback(self.try_to_start_autolock)
                if self.algorithm is not None:  # for mypy, algorithm is already set
                    self.algorithm.after_lock()

        except Exception:
            logger.exception("Error while handling new spectrum")
            self.stop()

    def start_manual_lock(self) -> None:
        # manual lock is just the simple algorithm with a lock point determined by the
        # `autolock_target_position` paramter
        self.parameters.autolock_mode.value = AutolockMode.SIMPLE
        self.control.exposed_write_registers()
        self.control.exposed_pause_acquisition()
        logger.info("Start manual lock.")
        self.parameters.lock.value = True
        self.control.exposed_write_registers()
        self.control.exposed_continue_acquisition()
