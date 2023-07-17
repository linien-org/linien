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

import logging
import pickle

from linien_common.common import check_plot_data, combine_error_signal, get_lock_point
from linien_server.autolock.algorithm_selection import AutolockAlgorithmSelector
from linien_server.autolock.robust import RobustAutolock
from linien_server.autolock.simple import SimpleAutolock

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Autolock:
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.first_error_signal = None
        self.first_error_signal_rolled = None
        self.parameters.autolock_running.value = False
        self.parameters.autolock_retrying.value = False

        self.should_watch_lock = False
        self._data_listener_added = False

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

    def run(
        self,
        x0,
        x1,
        spectrum,
        should_watch_lock=False,
        auto_offset=True,
        additional_spectra=None,
    ):
        """
        Start the autolock.

        If `should_watch_lock` is specified, the autolock continuously monitors the
        control and error signals after the lock was successful and tries to relock
        automatically using the spectrum that was recorded in the first run of the lock.
        """
        self.parameters.autolock_running.value = True
        self.parameters.autolock_preparing.value = True
        self.parameters.autolock_percentage.value = 0
        self.parameters.fetch_additional_signals.value = False
        self.x0, self.x1 = int(x0), int(x1)
        self.should_watch_lock = should_watch_lock

        # collect parameters that should be restored after stopping the lock
        self.parameters.autolock_initial_sweep_amplitude.value = (
            self.parameters.sweep_amplitude.value
        )

        self.additional_spectra = additional_spectra or []

        (
            self.first_error_signal,
            self.first_error_signal_rolled,
            self.line_width,
            self.peak_idxs,
        ) = self.record_first_error_signal(spectrum, auto_offset)

        try:
            self.autolock_mode_detector = AutolockAlgorithmSelector(
                self.parameters.autolock_mode_preference.value,
                spectrum,
                additional_spectra,
                self.line_width,
            )

            if self.autolock_mode_detector.done:
                self.start_autolock(self.autolock_mode_detector.mode)

        except Exception:
            # This may happen if `additional_spectra` contain uncorrelated data. Then
            # either autolock algorithm selector or `start_autolock` may raise a
            # spectrum uncorrelated exception
            logger.exception("Error while starting autolock")
            self.parameters.autolock_failed.value = True
            return self.exposed_stop()

        self.add_data_listener()

    def start_autolock(self, mode):
        logger.debug("start autolock with mode %s" % mode)
        self.parameters.autolock_mode.value = mode

        self.algorithm = [None, RobustAutolock, SimpleAutolock][mode](
            self.control,
            self.parameters,
            self.first_error_signal,
            self.first_error_signal_rolled,
            self.peak_idxs[0],
            self.peak_idxs[1],
            additional_spectra=self.additional_spectra,
        )

    def add_data_listener(self):
        if not self._data_listener_added:
            self._data_listener_added = True
            self.parameters.to_plot.add_callback(
                self.react_to_new_spectrum, call_with_first_value=False
            )

    def remove_data_listener(self):
        self._data_listener_added = False
        self.parameters.to_plot.remove_callback(self.react_to_new_spectrum)

    def react_to_new_spectrum(self, plot_data):
        """
        React to new spectrum data.

        If this is executed for the first time, a reference spectrum is recorded.

        If the autolock is approaching the desired line, a correlation function of the
        spectrum with the reference spectrum is calculated and the laser current is
        adapted such that the targeted line is centered.

        After this procedure is done, the real lock is turned on and after some time the
        lock is verified.

        If automatic relocking is desired, the control and error signals are
        continuously monitored after locking.
        """
        if self.parameters.pause_acquisition.value:
            return

        if plot_data is None or not self.parameters.autolock_running.value:
            return

        plot_data = pickle.loads(plot_data)
        if plot_data is None:
            return

        is_locked = self.parameters.lock.value

        # check that `plot_data` contains the information we need otherwise skip this
        # round
        if not check_plot_data(is_locked, plot_data):
            return

        try:
            if not is_locked:
                combined_error_signal = combine_error_signal(
                    (plot_data["error_signal_1"], plot_data.get("error_signal_2")),
                    self.parameters.dual_channel.value,
                    self.parameters.channel_mixing.value,
                    self.parameters.combined_offset.value,
                )

                if (
                    self.autolock_mode_detector is not None
                    and not self.autolock_mode_detector.done
                ):
                    self.autolock_mode_detector.handle_new_spectrum(
                        combined_error_signal
                    )
                    self.additional_spectra.append(combined_error_signal)

                    if self.autolock_mode_detector.done:
                        self.start_autolock(self.autolock_mode_detector.mode)
                    else:
                        return

                return self.algorithm.handle_new_spectrum(combined_error_signal)

            else:
                error_signal = plot_data["error_signal"]
                control_signal = plot_data["control_signal"]

                return self.after_lock(
                    error_signal, control_signal, plot_data.get("slow_control_signal")
                )

        except Exception:
            logger.exception("Error while handling new spectrum")
            self.parameters.autolock_failed.value = True
            self.exposed_stop()

    def record_first_error_signal(self, error_signal, auto_offset):
        (
            mean_signal,
            target_slope_rising,
            target_zoom,
            error_signal_rolled,
            line_width,
            peak_idxs,
        ) = get_lock_point(error_signal, self.x0, self.x1)

        self.central_y = int(mean_signal)

        if auto_offset:
            self.control.exposed_pause_acquisition()
            self.parameters.combined_offset.value = -1 * self.central_y
            error_signal -= self.central_y
            error_signal_rolled -= self.central_y
            self.additional_spectra = [
                s - self.central_y for s in self.additional_spectra
            ]
            self.control.exposed_write_registers()
            self.control.exposed_continue_acquisition()

        self.parameters.target_slope_rising.value = target_slope_rising
        self.control.exposed_write_registers()

        return error_signal, error_signal_rolled, line_width, peak_idxs

    def after_lock(self, error_signal, control_signal, slow_out):
        logger.debug("after lock")
        self.parameters.autolock_locked.value = True

        self.remove_data_listener()
        self.parameters.autolock_running.value = False

        self.algorithm.after_lock()

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
        self._reset_scan()

        # add a listener that listens for new spectrum data and consequently # tries to
        # relock.
        self.add_data_listener()

    def exposed_stop(self):
        """Abort any operation."""
        self.parameters.autolock_preparing.value = False
        self.parameters.autolock_percentage.value = 0
        self.parameters.autolock_running.value = False
        self.parameters.autolock_locked.value = False
        self.parameters.autolock_watching.value = False
        self.parameters.fetch_additional_signals.value = True
        self.remove_data_listener()

        self._reset_scan()
        self.parameters.task.value = None

    def _reset_scan(self):
        self.control.exposed_pause_acquisition()

        self.parameters.sweep_amplitude.value = (
            self.parameters.autolock_initial_sweep_amplitude.value
        )
        self.control.exposed_start_sweep()

        self.control.exposed_continue_acquisition()
