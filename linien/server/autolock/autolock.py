import pickle
import traceback

import numpy as np
from linien.common import (
    ANALOG_OUT0,
    check_plot_data,
    combine_error_signal,
    get_lock_point,
)
from linien.server.autolock.algorithm_selection import AutolockAlgorithmSelector
from linien.server.autolock.fast import FastAutolock
from linien.server.autolock.robust import RobustAutolock


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
        # we check each parameter before setting it because otherwise
        # this may crash the client if called very often (e.g.if the
        # autolock continuously fails)
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
        """Starts the autolock.

        If `should_watch_lock` is specified, the autolock continuously monitors
        the control and error signals after the lock was successful and tries to
        relock automatically using the spectrum that was recorded in the first
        run of the lock.
        """
        # FIXME: hier kann auch SpectrumUncorrelatedException auftauchen, entweder beim Auolock algorithm selector oder robust algorithm. Handlen!
        self.parameters.autolock_running.value = True
        self.parameters.autolock_preparing.value = True
        self.parameters.autolock_percentage.value = 0
        self.parameters.fetch_quadratures.value = False
        self.x0, self.x1 = int(x0), int(x1)
        self.should_watch_lock = should_watch_lock

        # collect parameters that should be restored after stopping the lock
        self.parameters.autolock_initial_ramp_amplitude.value = (
            self.parameters.ramp_amplitude.value
        )

        self.additional_spectra = additional_spectra or []

        (
            self.first_error_signal,
            self.first_error_signal_rolled,
            self.line_width,
            self.peak_idxs,
        ) = self.record_first_error_signal(spectrum, auto_offset)

        self.autolock_mode_detector = AutolockAlgorithmSelector(
            self.parameters.autolock_mode_preference.value,
            spectrum,
            additional_spectra,
            self.line_width,
        )

        if self.autolock_mode_detector.done:
            self.start_autolock(self.autolock_mode_detector.mode)

        self.add_data_listener()

    def start_autolock(self, mode):
        print("start autolock with mode", mode)
        self.parameters.autolock_mode.value = mode

        self.algorithm = [None, RobustAutolock, FastAutolock][mode](
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
            self.parameters.to_plot.on_change(
                self.react_to_new_spectrum, call_listener_with_first_value=False
            )

    def remove_data_listener(self):
        self._data_listener_added = False
        self.parameters.to_plot.remove_listener(self.react_to_new_spectrum)

    def react_to_new_spectrum(self, plot_data):
        """React to new spectrum data.

        If this is executed for the first time, a reference spectrum is
        recorded.

        If the autolock is approaching the desired line, a correlation
        function of the spectrum with the reference spectrum is calculated
        and the laser current is adapted such that the targeted line is centered.

        After this procedure is done, the real lock is turned on and after some
        time the lock is verified.

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

        # check that `plot_data` contains the information we need
        # otherwise skip this round
        if not check_plot_data(is_locked, plot_data):
            return

        try:
            if not is_locked:
                combined_error_signal = combine_error_signal(
                    (plot_data["error_signal_1"], plot_data["error_signal_2"]),
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

                if self.parameters.autolock_watching.value:
                    # the laser was locked successfully before. Now we check
                    # periodically whether the laser is still in lock
                    return self.watch_lock(error_signal, control_signal)

                else:
                    # we have started the lock.
                    # skip some data and check whether we really are in lock
                    # afterwards.
                    return self.after_lock(
                        error_signal, control_signal, plot_data.get("slow")
                    )

        except Exception:
            traceback.print_exc()
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
            self.control.pause_acquisition()
            self.parameters.combined_offset.value = -1 * self.central_y
            error_signal -= self.central_y
            error_signal_rolled -= self.central_y
            self.additional_spectra = [
                s - self.central_y for s in self.additional_spectra
            ]
            self.control.exposed_write_data()
            self.control.continue_acquisition()

        self.parameters.target_slope_rising.value = target_slope_rising
        self.control.exposed_write_data()

        return error_signal, error_signal_rolled, line_width, peak_idxs

    def after_lock(self, error_signal, control_signal, slow_out):
        """After locking, this method checks whether the laser really is locked.

        If desired, it automatically tries to relock if locking failed, or
        starts a watcher that does so over and over again.
        """

        def check_whether_in_lock(control_signal):
            """
            The laser is considered in lock if the mean value of the control
            signal is within the boundaries of the smallest current ramp we had
            before turning on the lock.
            """
            center = self.parameters.center.value
            initial_ampl = self.parameters.autolock_initial_ramp_amplitude.value
            target_zoom = 1
            ampl = initial_ampl / target_zoom

            slow_ramp = self.parameters.sweep_channel.value == ANALOG_OUT0
            slow_pid = self.parameters.pid_on_slow_enabled.value

            if not slow_ramp and not slow_pid:
                mean = np.mean(control_signal) / 8192
                return (center - ampl) <= mean <= (center + ampl)
            else:
                if slow_pid and not slow_ramp:
                    # we cannot handle this case. Just assume the laser is locked.
                    return True

                return (center - ampl) <= slow_out / 8192 <= (center + ampl)

        """self.parameters.autolock_locked.value = (
            check_whether_in_lock(control_signal)
            if self.parameters.check_lock.value
            else True
        )"""
        self.parameters.autolock_locked.value = True

        if self.parameters.autolock_locked.value and self.should_watch_lock:
            # we start watching the lock status from now on.
            # this is done in `react_to_new_spectrum()` which is called regularly.
            self.watcher_last_value = np.mean(control_signal) / 8192
            self.parameters.autolock_watching.value = True
        else:
            self.remove_data_listener()
            self.parameters.autolock_running.value = False

            if not self.parameters.autolock_locked.value:
                if self.should_watch_lock:
                    return self.relock()

                raise Exception("lock failed")

    def watch_lock(self, error_signal, control_signal):
        """Check whether the laser is still in lock and init a relock if not."""
        mean = np.mean(control_signal) / 8192

        diff = np.abs(mean - self.watcher_last_value)
        lock_lost = diff > self.parameters.watch_lock_threshold.value

        too_close_to_edge = np.abs(mean) > 0.95

        if too_close_to_edge or lock_lost:
            self.relock()

        self.watcher_last_value = mean

    def relock(self):
        """
        Relock the laser using the reference spectrum recorded in the first
        locking approach.
        """
        # we check each parameter before setting it because otherwise
        # this may crash the client if called very often (e.g.if the
        # autolock continuously fails)
        if not self.parameters.autolock_running.value:
            self.parameters.autolock_running.value = True
        if not self.parameters.autolock_retrying.value:
            self.parameters.autolock_retrying.value = True

        self.reset_properties()
        self._reset_scan()

        # add a listener that listens for new spectrum data and consequently
        # tries to relock.
        self.add_data_listener()

    def exposed_stop(self):
        """Abort any operation."""
        self.parameters.autolock_preparing.value = False
        self.parameters.autolock_percentage.value = 0
        self.parameters.autolock_running.value = False
        self.parameters.autolock_locked.value = False
        self.parameters.autolock_watching.value = False
        self.parameters.fetch_quadratures.value = True
        self.remove_data_listener()

        self._reset_scan()
        self.parameters.task.value = None

    def _reset_scan(self):
        self.control.pause_acquisition()

        self.parameters.ramp_amplitude.value = (
            self.parameters.autolock_initial_ramp_amplitude.value
        )
        self.control.exposed_start_ramp()

        self.control.continue_acquisition()
