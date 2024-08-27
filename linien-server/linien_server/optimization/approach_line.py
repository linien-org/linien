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

from time import time

import numpy as np
from linien_common.common import determine_shift_by_correlation
from linien_common.communication import LinienControlService

from ..parameters import Parameters

ZOOM_STEP = 2


class Approacher:
    def __init__(
        self,
        control: LinienControlService,
        parameters: Parameters,
        first_error_signal: np.ndarray,
        target_zoom: float,
        central_y: float,
        allow_sweep_speed_change: bool = False,
        wait_time_between_sweep_center_changes: float = 1.0,
    ):
        self.control = control
        self.parameters = parameters
        # central_y is the y coordinate between maximum and minimum of the target line
        # We vertically center the target line with respect to the x axis because
        # correlation doesn't work if the signal is only positive.
        self.first_error_signal = first_error_signal - central_y
        self.target_zoom = target_zoom
        self.allow_sweep_speed_change = allow_sweep_speed_change
        self.wait_time_between_sweep_center_changes = (
            wait_time_between_sweep_center_changes
        )
        self.central_y = central_y

        self.zoom_factor: float = 1.0
        self.n_at_this_zoom: int = 0
        self.last_shifts_at_this_zoom: list[float] = []
        self.time_of_last_sweep_center_shift: float = time()
        self.time_of_last_zoom: float = time()

    def approach_line(self, error_signal):
        if time() - self.time_of_last_zoom > 15:
            raise TimeoutError("Approaching took too long.")

        error_signal = error_signal - self.central_y

        # the autolock tries to center a line by changing the sweep center. If a line
        # was selected that is close to the edges, this can lead to a situation where
        # sweep center + sweep_amplitude > output limits of RP. In this case, we want to
        # ignore the error signal that was recorded at these points as it may contain a
        # distorted version of the spectrum that disturbs the correlation.
        initial_sweep_amplitude = self.parameters.sweep_amplitude.value
        sweep_amplitude = self.parameters.sweep_amplitude.value
        center = self.parameters.sweep_center.value
        sweep = (
            np.linspace(-sweep_amplitude, sweep_amplitude, len(error_signal)) + center
        )
        error_signal = np.array(error_signal)
        error_signal[np.abs(sweep) > 1] = np.nan

        # now, we calculate the correlation to find the shift
        shift, _, _ = determine_shift_by_correlation(
            self.zoom_factor, self.first_error_signal, error_signal
        )
        shift *= initial_sweep_amplitude

        if self.n_at_this_zoom == 0:
            # If we are at the final zoom, we should be very quick. Therefore, we change
            # the sweep center and turn the lock on immediately. We skip the rest of
            # this method (drift detection etc.)
            next_step_is_lock = self.zoom_factor >= self.target_zoom
            if next_step_is_lock:
                return True
            else:
                self.shift_sweep_center(shift)
        else:
            # wait for some time after the last sweep center shift
            if (
                time() - self.time_of_last_sweep_center_shift
                < self.wait_time_between_sweep_center_changes
            ):
                return

            # Check that the drift is slow. This is needed for systems that only react
            # slowly to changes in input parameters. In this case, we have to wait until
            # the reaction to the last input is done.
            shift_diff = np.abs(shift - self.last_shifts_at_this_zoom[-1])
            drift_is_slow = shift_diff < initial_sweep_amplitude / self.target_zoom / 8
            # if data comes in very slowly (<1 Hz), we skip the drift analysis because
            # it would take too much time
            recording_rate_is_low = self.parameters.sweep_speed.value > 10

            if recording_rate_is_low or drift_is_slow:
                is_close_to_target = shift < self.parameters.sweep_amplitude.value / 8
                if is_close_to_target:
                    return self.decrease_sweep_amplitude()

                else:
                    self.shift_sweep_center(shift)

        self.n_at_this_zoom += 1
        self.last_shifts_at_this_zoom.append(shift)

    def decrease_sweep_amplitude(self) -> None:
        self.n_at_this_zoom = 0
        self.last_shifts_at_this_zoom = []
        self.zoom_factor *= ZOOM_STEP
        self.time_of_last_zoom = time()

        self.control.exposed_pause_acquisition()
        self.parameters.sweep_amplitude.value /= ZOOM_STEP
        if self.allow_sweep_speed_change:
            new_sweep_speed = (
                self.parameters.sweep_speed.value - 1
                if self.parameters.sweep_speed.value > 5
                else self.parameters.sweep_speed.value
            )
            self.parameters.sweep_speed.value = new_sweep_speed
        self.control.exposed_write_registers()
        self.control.exposed_continue_acquisition()

    def shift_sweep_center(self, shift: float) -> None:
        self.control.exposed_pause_acquisition()
        self.time_of_last_sweep_center_shift = time()
        self.parameters.sweep_center.value -= shift
        self.control.exposed_write_registers()
        self.control.exposed_continue_acquisition()
