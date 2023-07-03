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

from time import time

import numpy as np
from linien_common.common import determine_shift_by_correlation

ZOOM_STEP = 2


class Approacher:
    def __init__(
        self,
        control,
        parameters,
        first_error_signal,
        target_zoom,
        central_y,
        allow_sweep_speed_change=False,
        wait_time_between_current_corrections=None,
    ):
        self.control = control
        self.parameters = parameters
        # central_y is the y coordinate between maximum and minimum of the
        # target line. We vertically center the target line with respect to the
        # x axis because correlation doesn't work if the signal is only positive
        self.first_error_signal = first_error_signal - central_y
        self.target_zoom = target_zoom
        self.allow_sweep_speed_change = allow_sweep_speed_change

        self.wait_time_between_current_corrections = (
            wait_time_between_current_corrections
        )

        self.central_y = central_y

        self.reset_properties()

    def reset_properties(self):
        self.history = []
        self.zoom_factor = 1
        self.N_at_this_zoom = 0
        self.last_shifts_at_this_zoom = None
        self.time_last_current_correction = None
        self.time_last_zoom = time()

    def approach_line(self, error_signal):
        if time() - self.time_last_zoom > 15:
            raise Exception("approaching took too long")

        error_signal = error_signal - self.central_y

        initial_sweep_amplitude = self.parameters.autolock_initial_sweep_amplitude.value

        # the autolock tries to center a line by changing the sweep center.
        # If a line was selected that is close to the edges, this can lead to
        # a situation where sweep center + sweep_amplitude > output limits of RP.
        # in this case, we want to ignore the error signal that was recorded at
        # these points as it may contain a distorted version of the spectrum that
        # disturbs the correlation.
        sweep_amplitude = self.parameters.sweep_amplitude.value
        center = self.parameters.sweep_center.value
        sweep = (
            np.linspace(-sweep_amplitude, sweep_amplitude, len(error_signal)) + center
        )
        error_signal = np.array(error_signal)
        error_signal[np.abs(sweep) > 1] = np.nan

        # now, we calculate the correlation to find the shift
        shift, zoomed_ref, zoomed_err = determine_shift_by_correlation(
            self.zoom_factor, self.first_error_signal, error_signal
        )
        shift *= initial_sweep_amplitude
        self.history.append((zoomed_ref, zoomed_err))
        self.history.append("shift %f" % (-1 * shift))

        if self.N_at_this_zoom == 0:
            # if we are at the final zoom, we should be very quick.
            # Therefore, we just correct the current and turn the lock on
            # immediately. We skip the rest of this method (drift detection etc.)
            next_step_is_lock = self.zoom_factor >= self.target_zoom
            if next_step_is_lock:
                return True
            else:
                self._correct_current(shift)
        else:
            # wait for some time after the last current correction
            min_wait_time = (
                1
                if self.wait_time_between_current_corrections is None
                else self.wait_time_between_current_corrections
            )
            if time() - self.time_last_current_correction < min_wait_time:
                return

            # check that the drift is slow
            # this is needed for systems that only react slowly to changes in
            # input parameters. In this case, we have to wait until the reaction
            # to the last input is done.
            shift_diff = np.abs(shift - self.last_shifts_at_this_zoom[-1])
            drift_slow = shift_diff < initial_sweep_amplitude / self.target_zoom / 8

            # if data comes in very slowly (<1 Hz), we skip the drift analysis
            # because it would take too much time
            low_recording_rate = self.parameters.sweep_speed.value > 10

            if low_recording_rate or drift_slow:
                is_close_to_target = shift < self.parameters.sweep_amplitude.value / 8
                if is_close_to_target:
                    return self._decrease_scan_range()
                else:
                    self._correct_current(shift)

        self.N_at_this_zoom += 1
        self.last_shifts_at_this_zoom = self.last_shifts_at_this_zoom or []
        self.last_shifts_at_this_zoom.append(shift)

    def _decrease_scan_range(self):
        self.N_at_this_zoom = 0
        self.last_shifts_at_this_zoom = None

        self.zoom_factor *= ZOOM_STEP
        self.time_last_zoom = time()

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

    def _correct_current(self, shift):
        self.control.exposed_pause_acquisition()
        self.time_last_current_correction = time()

        self.parameters.sweep_center.value -= shift

        self.control.exposed_write_registers()
        self.control.exposed_continue_acquisition()
