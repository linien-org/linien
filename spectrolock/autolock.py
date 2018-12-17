import numpy as np
from time import sleep
from scipy.signal import correlate
from matplotlib import pyplot as plt


class Autolock:
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.zoom_factor = 1
        self.first_error_signal = None
        self.skipped = 0
        self.history = []

    def run(self, x0, x1):
        self.x0, self.x1 = int(x0), int(x1)
        print(self.x0, self.x1, type(self.x0))

        """for x in (self.x0, self.x1):
            x /= 16384
            if x <= 1/(2*self.zoom_factor) or x >= 1 - (1/(2*self.zoom_factor)):
                # TODO: display message
                print('x not in range', x, 1/(2*self.zoom_factor), 1 - (1/(2*self.zoom_factor)))
                return"""

        self.parameters.to_plot.change(self.plot_data_received)

    def plot_data_received(self, plot_data):
        if plot_data is None or self.parameters.lock.value:
            return

        error_signal = plot_data[0]
        control_signal = plot_data[1]
        length = len(error_signal)

        if self.first_error_signal is None:
            # TODO: Should this only be allowed when fully zoomed out?
            cropped_data = np.array(error_signal[self.x0:self.x1])
            min_idx = np.argmin(cropped_data)
            max_idx = np.argmax(cropped_data)
            slope_data = cropped_data[min_idx:max_idx]
            zero_idx = self.x0 + min_idx + np.argmin(np.abs(slope_data))

            self.target_zoom = 16384 / (max_idx - min_idx) / 3

            error_signal = np.roll(error_signal, -int(zero_idx - (length/2)))
            self.first_error_signal = error_signal

            """new_ramp_center = self.parameters.center.value + \
                ((zero_idx - 0.5) * 2 * self.parameters.ramp_amplitude.value)

            self.parameters.ramp_amplitude.value /= self.zoom_factor"""
            #self.parameters.center.value = new_ramp_center
            #self.control.write_data()
            return

        if self.skipped < 30:
            self.skipped += 1
            return
        else:
            self.skipped = 0

        center_idx = 8192
        shift = int(length * (1/self.zoom_factor/2))
        zoomed_data = self.first_error_signal[center_idx - shift:center_idx + shift]

        control_signal_amplitude = (
            np.abs(np.min(control_signal[10:])) + np.max(control_signal[:-10])
        ) / 16384
        amplitude_target = self.parameters.ramp_amplitude.value

        """print('control signal amplitude is', control_signal_amplitude, 'target',
                amplitude_target)"""

        # check that the data received is new data, i.e. with the correct
        # scan range
        if np.abs(control_signal_amplitude - amplitude_target) / control_signal_amplitude < 0.2:
            self.history.append((zoomed_data, error_signal[::self.zoom_factor]))
            correlation = correlate(zoomed_data, error_signal[::self.zoom_factor])
            shift = np.argmax(correlation)
            shift = (shift - len(zoomed_data)) / len(zoomed_data) / 2

            self.zoom_factor *= 2
            self.control.write_data()
            self.history.append('shift %f' % (-1 * shift))
            print('final center', self.parameters.center.value)
            self.parameters.ramp_amplitude.value /= 2
            self.control.write_data()
            self.parameters.center.value -= shift
            self.control.write_data()

            if self.zoom_factor >= self.target_zoom:
                self.parameters.to_plot.remove_listener(self.plot_data_received)

                sleep(1)

                self.control.start_lock()
                self.parameters.task.reset()

                for hist in self.history:
                    if isinstance(hist, (tuple, list)):
                        zoomed_data, error_signal = hist
                        plt.plot(zoomed_data)
                        plt.plot(error_signal)
                        plt.show()
                    else:
                        print(hist)