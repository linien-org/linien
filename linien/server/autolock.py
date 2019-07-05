import pickle
import traceback
import numpy as np
from time import sleep, time
from linien.common import determine_shift_by_correlation, get_lock_point, \
    control_signal_has_correct_amplitude, combine_error_signal


class Autolock:
    """Spectroscopy autolock based on correlation."""
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.first_error_signal = None
        self.parameters.autolock_running.value = False
        self.should_watch_lock = False

        self.reset_properties()

    def reset_properties(self):
        self.history = []
        self.zoom_factor = 1
        self.N_at_this_zoom = 0
        self.last_shift_at_this_zoom = None
        self.skipped = 0
        self.parameters.autolock_failed.value = False
        self.parameters.autolock_locked.value = False
        self.parameters.autolock_watching.value = False

    def run(self, x0, x1, spectrum, should_watch_lock=False, auto_offset=True):
        """Starts the autolock.

        If `should_watch_lock` is specified, the autolock continuously monitors
        the control and error signals after the lock was successful and tries to
        relock automatically using the spectrum that was recorded in the first
        run of the lock.
        """
        self.parameters.autolock_running.value = True
        self.x0, self.x1 = int(x0), int(x1)
        self.should_watch_lock = should_watch_lock
        self.auto_offset = auto_offset

        self.parameters.autolock_approaching.value = True
        self.record_first_error_signal(spectrum)

        self.initial_ramp_amplitude = self.parameters.ramp_amplitude.value
        self.parameters.autolock_initial_ramp_amplitude.value = self.initial_ramp_amplitude
        self.initial_ramp_center = self.parameters.center.value

        self.add_data_listener()

    def add_data_listener(self):
        self.parameters.to_plot.change(self.react_to_new_spectrum)

    def remove_data_listener(self):
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

        if self.parameters.lock.value:
            error_signal = plot_data['error_signal']
            control_signal = plot_data['control_signal']
        else:
            combined_error_signal = combine_error_signal(
                (plot_data['error_signal_1'], plot_data['error_signal_2']),
                self.parameters.dual_channel.value,
                self.parameters.channel_mixing.value
            )

        try:
            if self.parameters.autolock_approaching.value:
                # we have already recorded a spectrum and are now approaching
                # the line by decreasing the scan range and adapting the
                # center current multiple times.

                if self.skipped < 3:
                    # after every step, we skip some data in order to let
                    # the laser equilibrate
                    self.skipped += 1
                    return

                self.skipped = 0

                return self.approach_line(combined_error_signal)

            elif self.parameters.autolock_watching.value:
                # the laser was locked successfully before. Now we check
                # periodically whether the laser is still in lock

                return self.watch_lock(error_signal, control_signal)

            else:
                # we are done with approaching and have started the lock.
                # skip some data and check whether we really are in lock
                # afterwards.

                if self.skipped < 3:
                    self.skipped += 1
                    return

                self.skipped = 0

                return self.after_lock(control_signal)

        except Exception:
            traceback.print_exc()
            self.exposed_stop()

    def record_first_error_signal(self, error_signal):
        mean_signal, target_slope_rising, target_zoom, rolled_error_signal = \
            get_lock_point(error_signal, self.x0, self.x1)

        if self.auto_offset:
            self.parameters.combined_offset.value = -1 * mean_signal
            # FIXME: disabled due to problem with conversion
            # rolled_error_signal -= mean_signal

        self.parameters.target_slope_rising.value = target_slope_rising
        self.control.exposed_write_data()

        self.target_zoom = target_zoom
        self.first_error_signal = rolled_error_signal

    def approach_line(self, error_signal):
        shift, zoomed_ref, zoomed_err = determine_shift_by_correlation(
            self.zoom_factor, self.first_error_signal, error_signal
        )
        shift *= self.initial_ramp_amplitude
        self.history.append((zoomed_ref, zoomed_err))

        self.control.exposed_write_data()
        self.history.append('shift %f' % (-1 * shift))

        self.parameters.center.value -= shift
        self.control.exposed_write_data()

        if self.N_at_this_zoom > 50:
            raise Exception('max number of N_at_this_zoom exceeded: %d' % self.N_at_this_zoom)

        if self.last_shift_at_this_zoom is not None:
            # check that the drift is slow
            # this is needed for systems that only react slowly to changes in
            # input parameters. In this case, we have to wait until the reaction
            # to the last input is done.
            drift_is_slow = (np.abs(shift - self.last_shift_at_this_zoom)) \
                            < (0.05 * self.parameters.ramp_amplitude.value)
            if drift_is_slow:
                self.N_at_this_zoom = 0
                self.last_shift_at_this_zoom = None

                zoom_step = 2
                self.zoom_factor *= zoom_step

                self.control.pause_acquisition()

                self.parameters.ramp_amplitude.value /= zoom_step
                self.control.exposed_write_data()

                if self.zoom_factor >= self.target_zoom:
                    self.parameters.autolock_approaching.value = False
                    self.control.exposed_start_lock()

                self.control.continue_acquisition()

        self.N_at_this_zoom += 1
        self.last_shift_at_this_zoom = shift

    def after_lock(self, control_signal):
        """After locking, this method checks whether the laser really is locked.

        If desired, it automatically tries to relock if locking failed, or
        starts a watcher that does so over and over again.
        """
        def check_whether_in_lock(control_signal):
            """
            The laser is considered in lock if the mean value of the control
            signal is within the boundaries of the smalles current ramp we had
            before turning on the lock.
            """
            mean = np.mean(control_signal) / 8192
            center = self.parameters.center.value
            ampl = self.parameters.ramp_amplitude.value
            return (center - ampl) <= mean <= (center + ampl)

        self.parameters.autolock_locked.value = check_whether_in_lock(control_signal)

        if self.parameters.autolock_locked.value and self.should_watch_lock:
            # we start watching the lock status from now on.
            # this is done in `react_to_new_spectrum()` which is called regularly.
            self.parameters.autolock_watching.value = True
        else:
            self.remove_data_listener()

            if not self.parameters.autolock_locked.value:
                if self.should_watch_lock:
                    return self.relock()

                self.control.exposed_reset()
                self.parameters.autolock_failed.value = True
                self.remove_data_listener()

            self.parameters.autolock_running.value = False

    def watch_lock(self, error_signal, control_signal):
        """Check whether the laser is still in lock and init a relock if not."""
        mean = np.abs(np.mean(control_signal) / 8192)
        still_in_lock = mean < 0.9

        if not still_in_lock:
            self.relock()

    def relock(self):
        """
        Relock the laser using the reference spectrum recorded in the first
        locking approach.
        """
        self.reset_properties()
        self.control.pause_acquisition()

        self.parameters.autolock_running.value = True
        self.parameters.autolock_approaching.value = True

        self.parameters.center.value = self.initial_ramp_center
        self.parameters.ramp_amplitude.value = self.initial_ramp_amplitude
        self.control.exposed_start_ramp()

        self.control.continue_acquisition()

        # add a listener that listens for new spectrum data and consequently
        # tries to relock.
        self.add_data_listener()

    def exposed_stop(self):
        """Abort any operation."""
        self.parameters.autolock_failed.value = True
        self.parameters.autolock_running.value = False
        self.parameters.autolock_locked.value = False
        self.parameters.autolock_approaching.value = False
        self.parameters.autolock_watching.value = False
        self.remove_data_listener()

        self.control.exposed_reset()