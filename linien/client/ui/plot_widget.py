import math
import pickle
import numpy as np
import pyqtgraph as pg

from time import time
from PyQt5 import QtGui, QtWidgets
from pyqtgraph.Qt import QtCore, QtGui

from linien.client.config import COLORS
from linien.client.widgets import CustomWidget
from linien.common import update_control_signal_history, determine_shift_by_correlation, \
    get_lock_point, control_signal_has_correct_amplitude, combine_error_signal


class PlotWidget(pg.PlotWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hideAxis('bottom')
        #self.hideAxis('left')

        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        # important: increasing pen width makes plotting much slower!
        # alternative: pg.setConfigOptions(useOpenGL=True)
        # see: https://github.com/pyqtgraph/pyqtgraph/issues/533
        pen_width = 1

        self.zero_line = pg.PlotCurveItem(pen=pg.mkPen('w', width=1))
        self.addItem(self.zero_line)
        self.signal1 = pg.PlotCurveItem(pen=pg.mkPen(COLORS['spectroscopy1'], width=pen_width))
        self.addItem(self.signal1)
        self.signal2 = pg.PlotCurveItem(pen=pg.mkPen(COLORS['spectroscopy2'], width=pen_width))
        self.addItem(self.signal2)
        self.combined_signal = pg.PlotCurveItem(pen=pg.mkPen(COLORS['spectroscopy_combined'], width=pen_width))
        self.addItem(self.combined_signal)

        self.control_signal = pg.PlotCurveItem(pen=pg.mkPen(COLORS['control_signal'], width=pen_width))
        self.addItem(self.control_signal)
        self.control_signal_history = pg.PlotCurveItem(pen=pg.mkPen(COLORS['control_signal_history'], width=pen_width))
        self.addItem(self.control_signal_history)
        self.slow_history = pg.PlotCurveItem(pen=pg.mkPen(COLORS['slow_history'], width=pen_width))
        self.addItem(self.slow_history)

        self.zero_line.setData([0, 16383], [0, 0])
        self.signal1.setData([0, 16383], [1, 1])
        self.signal1.setData([0, 16383], [1, 1])
        self.combined_signal.setData([0, 16383], [1, 1])

        self.connection = None
        self.parameters = None
        self.last_plot_rescale = 0
        self.last_plot_data = None
        self.plot_max = 0
        self.plot_min = np.inf
        self.touch_start = None
        self.autolock_ref_spectrum = None

        self.init_overlay()
        self.init_lock_target_line()

    def _to_data_coords(self, event):
        pos = self.plotItem.vb.mapSceneToView(event.pos())
        x, y = pos.x(), pos.y()
        return x, y

    def connection_established(self):
        self.control = self.app().control
        self.parameters = self.app().parameters

        self.control_signal_history_data = self.parameters.control_signal_history.value

        self.parameters.to_plot.change(self.replot)

    def mouseMoveEvent(self, event):
        if self.touch_start is None:
            return

        x0, y0 = self.touch_start

        x, y = self._to_data_coords(event)
        self.set_selection_overlay(x0, x - x0)

    def init_overlay(self):
        self.overlay = pg.LinearRegionItem(values=(-1000, -1000), movable=False)
        self.overlay.setVisible(False)
        self.addItem(self.overlay)

    def init_lock_target_line(self):
        self.lock_target_line = pg.InfiniteLine(movable=False)
        self.lock_target_line.setValue(1000)
        self.addItem(self.lock_target_line)

    def set_selection_overlay(self, x_start, width):
        self.overlay.setRegion((x_start, x_start + width))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        x, y = self._to_data_coords(event)

        self.touch_start = x, y
        self.set_selection_overlay(x, 0)
        self.overlay.setVisible(True)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if self.touch_start is None:
            return

        x, y = self._to_data_coords(event)
        x0, y0 = self.touch_start
        xdiff = np.abs(x0 - x)

        if xdiff / self.xmax < 0.01:
            # it was a click
            if not self.parameters.automatic_mode.value:
                self.graph_on_click(x0, y0)
        else:
            # it was a selection
            if self.parameters.automatic_mode.value:
                last_combined_error_signal = self.last_plot_data[2]
                self.control.start_autolock(
                    *sorted([x0, x]),
                    # we pickle it here because otherwise a netref is
                    # transmitted which blocks the autolock
                    pickle.dumps(last_combined_error_signal)
                )
                mean_signal, target_slope_rising, target_zoom, rolled_error_signal = \
                    get_lock_point(last_combined_error_signal, int(x0), int(x))
                self.autolock_ref_spectrum = rolled_error_signal
            else:
                self.graph_on_selection(x0, x)

        self.overlay.setVisible(False)
        self.touch_start = None

    @property
    def xmax(self):
        return len(self.last_plot_data[0]) - 1

    def graph_on_selection(self, x0, x):
        x0 /= self.xmax
        x /= self.xmax

        center = np.mean([x, x0])
        amplitude = np.abs(center - x) * 2
        center = (center - 0.5) * 2

        amplitude *= self.parameters.ramp_amplitude.value
        center = self.parameters.center.value + \
            (center * self.parameters.ramp_amplitude.value)

        self.parameters.ramp_amplitude.value = amplitude
        self.parameters.center.value = center
        self.control.write_data()

    def graph_on_click(self, x, y):
        center = x / self.xmax
        center = (center - 0.5) * 2
        center = self.parameters.center.value + \
            (center * self.parameters.ramp_amplitude.value)

        self.parameters.ramp_amplitude.value /= 2
        self.parameters.center.value = center
        self.control.write_data()

    def replot(self, to_plot):
        if self.parameters.pause_acquisition.value:
            return

        if to_plot is not None and not self.touch_start:
            to_plot = pickle.loads(to_plot)

            if to_plot is None:
                return

            # we also call this if the laser is not locked because it resets
            # the history in this case
            history, slow_history = self.update_control_signal_history(to_plot)

            if self.parameters.lock.value:
                self.last_plot_data = to_plot

                self.signal1.setVisible(False)
                self.signal2.setVisible(False)
                self.control_signal.setVisible(True)
                self.control_signal_history.setVisible(True)
                self.slow_history.setVisible(self.parameters.pid_on_slow_enabled.value)
                self.combined_signal.setVisible(True)

                error_signal, control_signal = to_plot['error_signal'], to_plot['control_signal']
                all_signals = (error_signal, control_signal, history, slow_history)

                self.plot_data_locked(to_plot)
                self.update_plot_scaling(all_signals)
                self.plot_autolock_target_line(None)
            else:
                self.signal1.setVisible(True)
                self.signal2.setVisible(self.parameters.dual_channel.value)
                self.combined_signal.setVisible(self.parameters.dual_channel.value)
                self.control_signal.setVisible(False)
                self.control_signal_history.setVisible(False)
                self.slow_history.setVisible(False)

                s1, s2 = to_plot['error_signal_1'], to_plot['error_signal_2']
                combined_error_signal = combine_error_signal(
                    (s1, s2),
                    self.parameters.dual_channel.value,
                    self.parameters.channel_mixing.value
                )
                all_signals = [s1, s2] + [combined_error_signal]
                self.last_plot_data = all_signals

                self.plot_data_unlocked((s1, s2), combined_error_signal)
                self.plot_autolock_target_line(combined_error_signal)
                self.update_plot_scaling(all_signals)

    def plot_data_unlocked(self, error_signals, combined_signal):
        error_signal1, error_signal2 = error_signals
        self.signal1.setData(list(range(len(error_signal1))), error_signal1)
        self.signal2.setData(list(range(len(error_signal2))), error_signal2)
        self.combined_signal.setData(list(range(len(combined_signal))), combined_signal)

    def plot_data_locked(self, signals):
        error_signal = signals['error_signal']
        control_signal = signals['control_signal']
        self.combined_signal.setData(list(range(len(error_signal))), error_signal)
        self.control_signal.setData(list(range(len(error_signal))), control_signal)

    def plot_autolock_target_line(self, combined_error_signal):
        if self.autolock_ref_spectrum is not None and self.parameters.autolock_approaching.value:
            ramp_amplitude = self.parameters.ramp_amplitude.value
            zoom_factor = 1 / ramp_amplitude
            initial_zoom_factor = 1 / self.parameters.autolock_initial_ramp_amplitude.value

            shift, _1, _2 = determine_shift_by_correlation(
                zoom_factor / initial_zoom_factor,
                self.autolock_ref_spectrum,
                combined_error_signal
            )
            shift *= zoom_factor / initial_zoom_factor
            length = len(combined_error_signal)
            shift = (length / 2) - (shift / 2* length)

            self.lock_target_line.setVisible(True)
            self.lock_target_line.setValue(shift)
        else:
            self.lock_target_line.setVisible(False)

    def update_plot_scaling(self, signals):
        if time() - self.last_plot_rescale > .5:
            all_ = []
            for signal in signals:
                all_ += signal
            self.plot_min = math.floor(np.min(all_))
            self.plot_max = math.ceil(np.max(all_))

            if self.plot_min == self.plot_max:
                self.plot_max += 1

            self.setYRange(self.plot_min, self.plot_max)

            self.last_plot_rescale = time()

    def update_control_signal_history(self, to_plot):
        self.control_history_data = update_control_signal_history(
            self.control_signal_history_data,
            to_plot,
            self.parameters.lock.value,
            self.parameters.control_signal_history_length.value
        )
        if self.parameters.lock.value:
            x_axis_length = 16384

            def scale(arr):
                timescale = self.parameters.control_signal_history_length.value
                if arr:
                    arr = np.array(arr)
                    arr -= arr[0]
                    arr *= 1 / timescale * x_axis_length
                return arr

            history = self.control_signal_history_data['values']
            self.control_signal_history.setData(
                scale(self.control_signal_history_data['times']),
                history
            )

            slow_values = self.control_signal_history_data['slow_values']
            self.slow_history.setData(
                scale(self.control_signal_history_data['slow_times']),
                slow_values
            )

            return history, slow_values
        return [], []