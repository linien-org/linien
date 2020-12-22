from linien.client.utils import peak_voltage_to_dBm
import math
import pickle
import numpy as np
import pyqtgraph as pg

from time import time
from PyQt5 import QtGui, QtWidgets
from pyqtgraph.Qt import QtCore, QtGui
from PyQt5.QtCore import QThread, pyqtSignal

from linien.config import DEFAULT_COLORS, N_COLORS
from linien.client.config import COLORS, DEFAULT_PLOT_RATE_LIMIT
from linien.gui.widgets import CustomWidget
from linien.common import get_signal_strength_from_i_q, update_control_signal_history, determine_shift_by_correlation, \
    get_lock_point, combine_error_signal, check_plot_data, N_POINTS, \
    SpectrumUncorrelatedException

# NOTE: this is required for using a pen_width > 1.
# There is a bug though that causes the plot to be way too small. Therefore,
# we call PlotWidget.resize() after a while
pg.setConfigOptions(
    useOpenGL=True,
    # by default, pyqtgraph tries to clean some things up using atexit.
    # This causes problems with rpyc objects as their connection is already
    # closed. Therefore, we disable this cleanup.
    exitCleanup=False
)

# relation between counts and 1V
V = 8192


class PlotWidget(pg.PlotWidget, CustomWidget):
    signal_power1 = pyqtSignal(float)
    signal_power2 = pyqtSignal(float)
    keyPressed = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hideAxis('bottom')
        #self.hideAxis('left')

        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        # NOTE: increasing the pen width requires OpenGL, otherwise painting
        # gets horribly slow.
        # See: https://github.com/pyqtgraph/pyqtgraph/issues/533
        # OpenGL is enabled in the beginning of this file.
        # NOTE: OpenGL has a bug that causes the plot to be way too small.
        # Therefore, self.resize() is called below.

        self.crosshair = pg.InfiniteLine(pos=N_POINTS / 2, pen=pg.mkPen('w', width=1))
        self.addItem(self.crosshair)

        self.zero_line = pg.PlotCurveItem(pen=pg.mkPen('w', width=1))
        self.addItem(self.zero_line)
        self.signal_strength_a = pg.PlotCurveItem()
        self.addItem(self.signal_strength_a)
        self.signal_strength_a2 = pg.PlotCurveItem()
        self.addItem(self.signal_strength_a2)
        self.signal_strength_a_fill = pg.FillBetweenItem(self.signal_strength_a, self.signal_strength_a2)
        self.addItem(self.signal_strength_a_fill)
        self.signal_strength_b = pg.PlotCurveItem()
        self.addItem(self.signal_strength_b)
        self.signal_strength_b2 = pg.PlotCurveItem()
        self.addItem(self.signal_strength_b2)
        self.signal_strength_b_fill = pg.FillBetweenItem(self.signal_strength_b, self.signal_strength_b2)
        self.addItem(self.signal_strength_b_fill)
        self.signal1 = pg.PlotCurveItem()
        self.addItem(self.signal1)
        self.signal2 = pg.PlotCurveItem()
        self.addItem(self.signal2)
        self.combined_signal = pg.PlotCurveItem()
        self.addItem(self.combined_signal)

        self.control_signal = pg.PlotCurveItem()
        self.addItem(self.control_signal)
        self.control_signal_history = pg.PlotCurveItem()
        self.addItem(self.control_signal_history)
        self.slow_history = pg.PlotCurveItem()
        self.addItem(self.slow_history)

        self.zero_line.setData([0, N_POINTS - 1], [0, 0])
        self.signal1.setData([0, N_POINTS - 1], [1, 1])
        self.signal1.setData([0, N_POINTS - 1], [1, 1])
        self.combined_signal.setData([0, N_POINTS - 1], [1, 1])

        self.connection = None
        self.parameters = None
        self.last_plot_rescale = 0
        self.last_plot_data = None
        self.plot_max = 0
        self.plot_min = np.inf
        self.touch_start = None
        self.autolock_ref_spectrum = None

        self.selection_running = False
        self.selection_boundaries = None

        self.init_overlays()
        self.init_lock_target_line()

        self._fixed_opengl_bug = False

        self.enable_area_selection()

        self.last_plot_time = 0
        self.plot_rate_limit = DEFAULT_PLOT_RATE_LIMIT

    def _to_data_coords(self, event):
        pos = self.plotItem.vb.mapSceneToView(event.pos())
        x, y = pos.x(), pos.y()
        return x, y

    def connection_established(self):
        self.control = self.app().control
        self.parameters = self.app().parameters

        def set_pens(color):
            pen_width = self.parameters.plot_line_width.value

            for curve, name in {
                self.signal1: 'spectrum_1',

                self.signal2: 'spectrum_2',
                self.combined_signal: 'spectrum_combined',
                self.control_signal: 'control_signal',
                self.control_signal_history: 'control_signal_history',
                self.slow_history: 'slow_history',
            }.items():
                color_idx = COLORS[name]
                r, g, b, *stuff = getattr(self.parameters, 'plot_color_%d' % color_idx).value
                a = self.parameters.plot_line_opacity.value
                curve.setPen(pg.mkPen(
                    (r, g, b, a), width=pen_width
                ))

        for color_idx in range(N_COLORS):
            getattr(self.parameters, 'plot_color_%d' % color_idx).change(set_pens)
        self.parameters.plot_line_width.change(set_pens)
        self.parameters.plot_line_opacity.change(set_pens)

        self.control_signal_history_data = self.parameters.control_signal_history.value

        self.parameters.to_plot.change(self.replot)

        def autolock_selection_changed(value):
            if value:
                self.parameters.optimization_selection.value = False
                self.enable_area_selection(selectable_width=.75)
            elif not self.parameters.optimization_selection.value:
                self.disable_area_selection()
        self.parameters.autolock_selection.change(autolock_selection_changed)

        def optimization_selection_changed(value):
            if value:
                self.parameters.autolock_selection.value = False
                self.enable_area_selection(selectable_width=.75)
            elif not self.parameters.autolock_selection.value:
                self.disable_area_selection()
        self.parameters.optimization_selection.change(optimization_selection_changed)

        def show_or_hide_crosshair(automatic_mode):
            self.crosshair.setVisible(not automatic_mode)
        self.parameters.automatic_mode.change(show_or_hide_crosshair)


    def mouseMoveEvent(self, event):
        if self.touch_start is None:
            return

        x0, y0 = self.touch_start

        x, y = self._to_data_coords(event)
        x = self._within_boundaries(x)
        self.set_selection_overlay(x0, x - x0)

    def init_overlays(self):
        self.overlay = pg.LinearRegionItem(values=(0, 0), movable=False)
        self.overlay.setVisible(False)
        self.addItem(self.overlay)

        self.boundary_overlays = [
            pg.LinearRegionItem(
                values=(0, 0),
                movable=False,
                brush=(0, 0, 0, 200),
            )
            for i in range(2)
        ]
        for i, overlay in enumerate(self.boundary_overlays):
            overlay.setVisible(False)
            # make outer borders invisible, see
            # https://github.com/pyqtgraph/pyqtgraph/issues/462
            overlay.lines[i].setPen((0, 0, 0, 0))
            self.addItem(overlay)

    def init_lock_target_line(self):
        self.lock_target_line = pg.InfiniteLine(movable=False)
        self.lock_target_line.setValue(1000)
        self.addItem(self.lock_target_line)

    def set_selection_overlay(self, x_start, width):
        self.overlay.setRegion((x_start, x_start + width))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        if event.button() == QtCore.Qt.RightButton:
            return

        x, y = self._to_data_coords(event)

        if not self.selection_running:
            return

        if self.selection_running:
            if x < self.selection_boundaries[0] or x > self.selection_boundaries[1]:
                return

        self.touch_start = x, y
        self.set_selection_overlay(x, 0)
        self.overlay.setVisible(True)

    def _within_boundaries(self, x):
        boundaries = self.selection_boundaries if self.selection_running \
            else [0, N_POINTS]

        if x < boundaries[0]:
            return boundaries[0]
        if x > boundaries[1]:
            return boundaries[1]
        return x

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if self.touch_start is None:
            return

        x, y = self._to_data_coords(event)
        x = self._within_boundaries(x)
        x0, y0 = self.touch_start
        xdiff = np.abs(x0 - x)

        if xdiff / self.xmax < 0.01:
            # it was a click
            pass
        else:
            # it was a selection
            if self.selection_running:
                # we pickle it here because otherwise a netref is
                # transmitted which blocks the autolock
                if self.parameters.autolock_selection.value:
                    last_combined_error_signal = self.last_plot_data[2]
                    self.parameters.autolock_selection.value = False

                    self.control.start_autolock(*sorted([x0, x]), pickle.dumps(last_combined_error_signal))

                    mean_signal, target_slope_rising, target_zoom, rolled_error_signal = \
                        get_lock_point(last_combined_error_signal, *sorted((int(x0), int(x))))
                    self.autolock_ref_spectrum = rolled_error_signal
                elif self.parameters.optimization_selection.value:
                    dual_channel = self.parameters.dual_channel.value
                    channel = self.parameters.optimization_channel.value
                    spectrum = self.last_plot_data[
                        0 if not dual_channel else (0, 1)[channel]
                    ]
                    self.parameters.optimization_selection.value = False
                    points = sorted([int(x0), int(x)])
                    self.control.start_optimization(*points, pickle.dumps(spectrum))

        self.overlay.setVisible(False)
        self.touch_start = None

    @property
    def xmax(self):
        return len(self.last_plot_data[0]) - 1

    def replot(self, to_plot):
        time_beginning = time()
        if time_beginning - self.last_plot_time <= self.plot_rate_limit:
            # don't plot too often at it only causes unnecessary load
            return
        self.last_plot_time = time_beginning

        # NOTE: this is necessary if OpenGL is activated. Otherwise, the
        # plot is way too small. This command apparently causes a repaint
        # and works fine even though the values are nonsense.
        if not self._fixed_opengl_bug:
            self._fixed_opengl_bug = True
            self.resize(
                self.parent().frameGeometry().width(),
                self.parent().frameGeometry().height()
            )

        if self.parameters.pause_acquisition.value:
            return

        if to_plot is not None and not self.touch_start:
            to_plot = pickle.loads(to_plot)

            if to_plot is None:
                return

            if not check_plot_data(self.parameters.lock.value, to_plot):
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
                self.signal_strength_a.setVisible(False)
                self.signal_strength_b.setVisible(False)
                self.signal_strength_a2.setVisible(False)
                self.signal_strength_b2.setVisible(False)
                self.signal_strength_a_fill.setVisible(False)
                self.signal_strength_b_fill.setVisible(False)

                error_signal, control_signal = to_plot['error_signal'], to_plot['control_signal']
                all_signals = (error_signal, control_signal, history, slow_history)

                self.plot_data_locked(to_plot)
                self.update_plot_scaling(all_signals)
                self.plot_autolock_target_line(None)
            else:
                dual_channel = self.parameters.dual_channel.value
                self.signal1.setVisible(True)
                self.signal2.setVisible(dual_channel)
                self.combined_signal.setVisible(dual_channel)
                self.control_signal.setVisible(False)
                self.control_signal_history.setVisible(False)
                self.slow_history.setVisible(False)

                s1, s2 = to_plot['error_signal_1'], to_plot['error_signal_2']
                combined_error_signal = combine_error_signal(
                    (s1, s2),
                    dual_channel,
                    self.parameters.channel_mixing.value,
                    self.parameters.combined_offset.value
                )
                all_signals = [s1, s2] + [combined_error_signal]
                self.last_plot_data = all_signals

                self.plot_data_unlocked((s1, s2), combined_error_signal)
                self.plot_autolock_target_line(combined_error_signal)

                if 'error_signal_1_quadrature' in to_plot:
                    self.signal_strength_a.setVisible(True)
                    self.signal_strength_b.setVisible(dual_channel)
                    self.signal_strength_a2.setVisible(True)
                    self.signal_strength_b2.setVisible(dual_channel)
                    self.signal_strength_a_fill.setVisible(True)
                    self.signal_strength_b_fill.setVisible(dual_channel)

                    s1q, s2q = to_plot['error_signal_1_quadrature'], to_plot['error_signal_2_quadrature']

                    max_signal_strength_V = self.plot_signal_strength(
                        s1, s1q, self.signal_strength_a, self.signal_strength_a2,
                        self.signal_strength_a_fill,
                        self.parameters.offset_a.value,
                        self.parameters.plot_color_0.value
                    ) / V
                    max_signal_strength2_V = self.plot_signal_strength(
                        s2, s2q, self.signal_strength_b, self.signal_strength_b2,
                        self.signal_strength_b_fill,
                        self.parameters.offset_b.value,
                        self.parameters.plot_color_1.value
                    ) / V

                    all_signals.append([
                        max_signal_strength_V * V, -1 * max_signal_strength_V * V,
                    ])
                    if dual_channel:
                        all_signals.append([
                            max_signal_strength2_V * V, -1 * max_signal_strength2_V * V
                        ])

                    self.signal_power1.emit(peak_voltage_to_dBm(max_signal_strength_V))
                    self.signal_power2.emit(peak_voltage_to_dBm(max_signal_strength2_V))
                else:
                    self.signal_strength_a.setVisible(False)
                    self.signal_strength_b.setVisible(False)
                    self.signal_strength_a2.setVisible(False)
                    self.signal_strength_b2.setVisible(False)
                    self.signal_strength_a_fill.setVisible(False)
                    self.signal_strength_b_fill.setVisible(False)

                    self.signal_power1.emit(-1000)
                    self.signal_power2.emit(-1000)

                self.update_plot_scaling(all_signals)

        time_end = time()
        time_diff = time_end - time_beginning
        new_rate_limit = 2 * time_diff

        if new_rate_limit < DEFAULT_PLOT_RATE_LIMIT:
            new_rate_limit = DEFAULT_PLOT_RATE_LIMIT

        self.plot_rate_limit = new_rate_limit

    def plot_signal_strength(self, i, q, signal, neg_signal, fill, channel_offset, color):
        # we have to subtract channel offset here and will add it back in the end
        i -= int(round(channel_offset))
        q -= int(round(channel_offset))
        signal_strength = get_signal_strength_from_i_q(i, q)

        r,g,b, *stuff = color

        x = list(range(len(signal_strength)))
        signal_strength_scaled = signal_strength / V
        upper = (channel_offset / V) + signal_strength_scaled
        lower = (channel_offset / V) -1 * signal_strength_scaled

        brush = pg.mkBrush(r, g, b, self.parameters.plot_fill_opacity.value)
        fill.setBrush(brush)

        invisible_pen = pg.mkPen('k', width=0.00001)
        signal.setData(x, upper, pen=invisible_pen)
        neg_signal.setData(x, lower, pen=invisible_pen)
        return np.max([
            np.max(upper),
            -1 * np.min(lower)
        ]) * V

    def plot_data_unlocked(self, error_signals, combined_signal):
        error_signal1, error_signal2 = error_signals
        self.signal1.setData(list(range(len(error_signal1))), error_signal1 / V)
        self.signal2.setData(list(range(len(error_signal2))), error_signal2 / V)
        self.combined_signal.setData(list(range(len(combined_signal))), combined_signal / V)

    def plot_data_locked(self, signals):
        error_signal = signals['error_signal']
        control_signal = signals['control_signal']
        self.combined_signal.setData(list(range(len(error_signal))), error_signal / V)
        self.control_signal.setData(list(range(len(error_signal))), control_signal / V)

    def plot_autolock_target_line(self, combined_error_signal):
        if self.autolock_ref_spectrum is not None and self.parameters.autolock_approaching.value:
            ramp_amplitude = self.parameters.ramp_amplitude.value
            zoom_factor = 1 / ramp_amplitude
            initial_zoom_factor = 1 / self.parameters.autolock_initial_ramp_amplitude.value

            try:
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

            except SpectrumUncorrelatedException:
                self.lock_target_line.setVisible(False)
        else:
            self.lock_target_line.setVisible(False)


    def keyPressEvent(self, event):
        # we listen here in addition to the main window because some events
        # are only caught here
        self.keyPressed.emit(event.key())

    def update_plot_scaling(self, signals):
        if time() - self.last_plot_rescale > .5:
            all_ = np.array([])
            for signal in signals:
                all_ = np.append(all_, signal)

            if self.parameters.autoscale_y.value:
                self.plot_min = np.min(all_) / V
                self.plot_max = np.max(all_) / V
            else:
                limit = self.parameters.y_axis_limits.value
                self.plot_min, self.plot_max = -limit, limit

            if self.plot_min == self.plot_max:
                self.plot_max += 0.0001

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
            x_axis_length = N_POINTS

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
                np.array(history) / V
            )

            slow_values = self.control_signal_history_data['slow_values']
            self.slow_history.setData(
                scale(self.control_signal_history_data['slow_times']),
                np.array(slow_values) / V
            )

            return history, slow_values
        return [], []

    def enable_area_selection(self, selectable_width=0.5):
        self.selection_running = True

        # there are some glitches if the width of the overlay is exactly right.
        # Therefore we make it a little wider.
        extra_width = N_POINTS / 100
        x_axis_length = N_POINTS
        boundary_width = (x_axis_length * (1 - selectable_width)) / 2.0

        self.selection_boundaries = (boundary_width, x_axis_length - boundary_width)

        self.boundary_overlays[0].setRegion((-extra_width, boundary_width))
        self.boundary_overlays[1].setRegion((x_axis_length - boundary_width, x_axis_length + extra_width))

        for overlay in self.boundary_overlays:
            overlay.setVisible(True)

    def disable_area_selection(self):
        self.selection_running = False

        for overlay in self.boundary_overlays:
            overlay.setVisible(False)