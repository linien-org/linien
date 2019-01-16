import pickle
import traceback
import numpy as np
from time import sleep, time
from scipy.signal import correlate


class Autolock:
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.zoom_factor = 1
        self.first_error_signal = None
        self.skipped = 0
        self.history = []
        self.failed = False
        self.running = False

    def run(self, x0, x1):
        self.running = True
        self.x0, self.x1 = int(x0), int(x1)

        self.parameters.to_plot.change(self.react_to_new_spectrum)

    def emit_status(self):
        # re-assign the task such that the change information is propagated
        self.parameters.task.value = self

    def react_to_new_spectrum(self, plot_data):
        if plot_data is None or not self.running:
            return

        plot_data = pickle.loads(plot_data)
        if plot_data is None:
            return

        error_signal = plot_data[0]
        control_signal = plot_data[1]

        try:
            if self.first_error_signal is None:
                # the auto lock just started
                self.approaching = True
                self.emit_status()
                return self.record_first_error_signal(error_signal)

            if self.approaching:
                if self.skipped < 5:
                    # after every step, we skip some data in order to let
                    # the laser equilibrate
                    self.skipped += 1
                    return

                self.skipped = 0
                return self.approach_line(error_signal, control_signal)
            else:
                # we are done with approaching and have started the lock.
                # skip some data and check whether we really are in lock
                # afterwards.
                if self.skipped < 15:
                    self.skipped += 1
                    return

                self.parameters.to_plot.remove_listener(self.react_to_new_spectrum)

                in_lock = self.check_whether_in_lock(control_signal)

                if not in_lock:
                    self.control.reset()
                    self.failed = True

                self.running = False
                self.emit_status()

                """for hist in self.history:
                    if isinstance(hist, (tuple, list)):
                        zoomed_data, error_signal = hist
                        plt.plot(zoomed_data)
                        plt.plot(error_signal)
                        plt.show()
                    else:
                        print(hist)"""

        except Exception:
            traceback.print_exc()
            self.stop()

    def record_first_error_signal(self, error_signal):
        # TODO: Should this only be allowed when fully zoomed out?
        length = len(error_signal)
        cropped_data = np.array(error_signal[self.x0:self.x1])
        min_idx = np.argmin(cropped_data)
        max_idx = np.argmax(cropped_data)

        mean_signal = np.mean([cropped_data[min_idx], cropped_data[max_idx]])
        slope_data = np.array(cropped_data[min_idx:max_idx]) - mean_signal
        self.parameters.offset.value -= mean_signal

        zero_idx = self.x0 + min_idx + np.argmin(np.abs(slope_data))

        self.target_zoom = 16384 / (max_idx - min_idx) / 3

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
            shift = np.argmax(correlation) * skip_factor
            shift = (shift - len(zoomed_data)) / len(zoomed_data) * 2 / self.zoom_factor

            self.control.write_data()
            self.history.append('shift %f' % (-1 * shift))

            self.zoom_factor *= 2
            self.parameters.ramp_amplitude.value /= 2
            self.control.write_data()

            self.parameters.center.value -= shift
            self.control.write_data()

            if self.zoom_factor >= self.target_zoom:
                self.approaching = False
                self.emit_status()
                self.control.start_lock()

    def check_whether_in_lock(self, control_signal):
        mean = np.mean(control_signal) / 8192
        center = self.parameters.center.value
        ampl = self.parameters.ramp_amplitude.value
        return (center - ampl) <= mean <= (center + ampl)

    def stop(self):
        self.failed = True
        self.running = False
        self.control.reset()
        self.emit_status()