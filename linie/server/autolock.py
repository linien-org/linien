import pickle
import traceback
import numpy as np
from time import sleep, time
from scipy.signal import correlate


class Autolock:
    """Spectroscopy autolock based on correlation."""
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.first_error_signal = None
        self.exposed_running = False
        self.should_watch_lock = False

        self.reset_properties()

    def reset_properties(self):
        self.history = []
        self.zoom_factor = 1
        self.N_at_this_zoom = 0
        self.skipped = 0
        self.exposed_failed = False
        self.exposed_locked = False
        self.exposed_watching = False

    def run(self, x0, x1, spectrum, should_watch_lock=False):
        """Starts the autolock.

        If `should_watch_lock` is specified, the autolock continuously monitors
        the control and error signals after the lock was successful and tries to
        relock automatically using the spectrum that was recorded in the first
        run of the lock.
        """
        self.exposed_running = True
        self.x0, self.x1 = int(x0), int(x1)
        self.should_watch_lock = should_watch_lock

        self.approaching = True
        self.emit_status()
        self.record_first_error_signal(spectrum)

        self.add_data_listener()

    def add_data_listener(self):
        self.parameters.to_plot.change(self.react_to_new_spectrum)

    def emit_status(self):
        """Sets the `task` parameter again such that the change information is propagated"""
        self.parameters.task.value = self

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

        if plot_data is None or not self.exposed_running:
            return

        plot_data = pickle.loads(plot_data)
        if plot_data is None:
            return

        error_signal, control_signal = plot_data

        try:
            if self.approaching:
                # we have already recorded a spectrum and are now approaching
                # the line by decreasing the scan range and adapting the
                # center current multiple times.

                if self.skipped < 5:
                    # after every step, we skip some data in order to let
                    # the laser equilibrate
                    self.skipped += 1
                    return

                self.skipped = 0

                return self.approach_line(error_signal, control_signal)

            elif self.exposed_watching:
                # the laser was locked successfully before. Now we check
                # periodically whether the laser is still in lock

                return self.watch_lock(error_signal, control_signal)

            else:
                # we are done with approaching and have started the lock.
                # skip some data and check whether we really are in lock
                # afterwards.

                if self.skipped < 10:
                    self.skipped += 1
                    return

                self.skipped = 0

                return self.after_lock(control_signal)

        except Exception:
            traceback.print_exc()
            self.exposed_stop()

    def record_first_error_signal(self, error_signal):
        # TODO: Should this only be allowed when fully zoomed out?
        length = len(error_signal)
        cropped_data = np.array(error_signal[self.x0:self.x1])
        min_idx = np.argmin(cropped_data)
        max_idx = np.argmax(cropped_data)

        mean_signal = np.mean([cropped_data[min_idx], cropped_data[max_idx]])
        slope_data = np.array(cropped_data[min_idx:max_idx]) - mean_signal
        self.parameters.offset.value -= mean_signal
        self.parameters.target_slope_rising.value = max_idx > min_idx
        self.control.exposed_write_data()

        zero_idx = self.x0 + min_idx + np.argmin(np.abs(slope_data))

        self.target_zoom = 16384 / (max_idx - min_idx) / 1.5

        error_signal = np.roll(error_signal, -int(zero_idx - (length/2)))
        self.first_error_signal = error_signal

    def approach_line(self, error_signal, control_signal):
        length = len(error_signal)
        center_idx = int(length / 2)

        shift = int(length * (1/self.zoom_factor/2))
        zoomed_data = self.first_error_signal[center_idx - shift:center_idx + shift]

        control_signal_center = control_signal[100:-100]
        control_signal_amplitude = (
            np.max(control_signal_center) - np.min(control_signal_center)
        ) / 16384
        amplitude_target = self.parameters.ramp_amplitude.value

        # check that the data received is new data, i.e. with the correct
        # scan range
        if np.abs(control_signal_amplitude - amplitude_target) / control_signal_amplitude < 0.2:
            self.history.append((zoomed_data, error_signal[::self.zoom_factor]))

            # correlation is slow on red pitaya --> use at maximum 4096 points
            skip_factor = int(len(zoomed_data) / 4096)
            if skip_factor < 1:
                skip_factor = 1

            correlation = correlate(zoomed_data[::skip_factor], error_signal[::self.zoom_factor][::skip_factor])
            print('CORRELATION', np.max(correlation))
            shift = np.argmax(correlation) * skip_factor
            shift = (shift - len(zoomed_data)) / len(zoomed_data) * 2 / self.zoom_factor
            print('N', self.N_at_this_zoom, 'SHIFT', shift)

            self.control.exposed_write_data()
            self.history.append('shift %f' % (-1 * shift))

            self.parameters.center.value -= shift
            self.control.exposed_write_data()

            self.N_at_this_zoom += 1

            if self.N_at_this_zoom > 2:
                self.N_at_this_zoom = 0

                self.zoom_factor *= 2
                self.parameters.ramp_amplitude.value /= 2
                self.control.exposed_write_data()

                if self.zoom_factor >= self.target_zoom:
                    self.approaching = False
                    self.emit_status()
                    self.control.exposed_start_lock()

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

        self.exposed_locked = check_whether_in_lock(control_signal)

        if self.exposed_locked and self.should_watch_lock:
            # we start watching the lock status from now on.
            # this is done in `react_to_new_spectrum()` which is called regularly.
            self.exposed_watching = True
        else:
            self.parameters.to_plot.remove_listener(self.react_to_new_spectrum)

            if not self.exposed_locked:
                if self.should_watch_lock:
                    return self.relock()

                self.control.exposed_reset()
                self.exposed_failed = True

            self.exposed_running = False

        self.emit_status()

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
        self.exposed_running = True
        self.approaching = True

        self.parameters.center.value = 0
        self.parameters.ramp_amplitude.value = 1
        self.control.exposed_start_ramp()

        self.emit_status()

        # add a listener that listens for new spectrum data and consequently
        # tries to relock.
        self.add_data_listener()

    def exposed_stop(self):
        """Abort any operation."""
        self.exposed_failed = True
        self.exposed_running = False
        self.exposed_locked = False
        self.approaching = False
        self.exposed_watching = False

        self.control.exposed_reset()
        self.emit_status()