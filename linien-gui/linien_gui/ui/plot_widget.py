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

import pickle
from time import time

import numpy as np
import pyqtgraph as pg
from linien_common.common import (
    DECIMATION,
    N_POINTS,
    SpectrumUncorrelatedException,
    check_plot_data,
    combine_error_signal,
    determine_shift_by_correlation,
    get_lock_point,
    get_signal_strength_from_i_q,
    update_signal_history,
)
from linien_gui.config import DEFAULT_PLOT_RATE_LIMIT, N_COLORS, Color
from linien_gui.utils import get_linien_app_instance
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal
from pyqtgraph.Qt import QtCore

# NOTE: this is required for using a pen_width > 1. There is a bug though that causes
# the plot to be way too small. Therefore, we call PlotWidget.resize() after a while
pg.setConfigOptions(
    useOpenGL=True,
    # by default, pyqtgraph tries to clean some things up using atexit. This causes
    # problems with rpyc objects as their connection is already closed. Therefore, we
    # disable this cleanup.
    exitCleanup=False,
)

# relation between counts and 1V
V = 8192

# pyqt signals enforce type, so...
INVALID_POWER = -1000


def peak_voltage_to_dBm(voltage):
    return 10 + 20 * np.log10(voltage)


class TimeXAxis(pg.AxisItem):
    """Plots x axis as time in seconds instead of point number."""

    def __init__(self, *args, parent=None, **kwargs):
        pg.AxisItem.__init__(self, *args, **kwargs)
        self.parent = parent
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

    def on_connection_established(self):
        # we have to wait until parameters (of parent) is available
        QtCore.QTimer.singleShot(100, self.listen_to_parameter_changes)

    def listen_to_parameter_changes(self):
        self.parent.parameters.sweep_speed.add_callback(self.force_repaint_tick_strings)
        self.parent.parameters.lock.add_callback(self.force_repaint_tick_strings)
        self.force_repaint_tick_strings()

    def force_repaint_tick_strings(self, *args):
        self.picture = None
        self.update()

    def tickStrings(self, values, scale, spacing):
        locked = self.parent.parameters.lock.value
        sweep_speed = self.parent.parameters.sweep_speed.value if not locked else 0
        time_between_points = (1 / 125e6) * 2 ** (sweep_speed) * DECIMATION
        values = [v * time_between_points for v in values]
        spacing *= time_between_points

        places = max(0, np.ceil(-np.log10(spacing * scale)))
        strings = []
        for v in values:
            vs = v * scale
            if abs(vs) < 0.001 or abs(vs) >= 10000:
                vstr = "%g" % vs
            else:
                vstr = ("%%0.%df" % places) % vs
            strings.append(vstr)
        return strings


class PlotWidget(pg.PlotWidget):
    signal_power1 = pyqtSignal(float)
    signal_power2 = pyqtSignal(float)
    keyPressed = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super(PlotWidget, self).__init__(
            *args,
            axisItems={"bottom": TimeXAxis(parent=self, orientation="bottom")},
            **kwargs,
        )
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.getAxis("bottom").enableAutoSIPrefix(False)
        self.showGrid(x=True, y=True)
        self.setLabel("bottom", "time", units="s")

        # Causes auto-scale button (‘A’ in lower-left corner) to be hidden for this
        # PlotItem
        self.hideButtons()
        # we have our own "reset view" button instead
        self.init_reset_view_button()

        # copied from https://github.com/pyqtgraph/pyqtgraph/blob/master/pyqtgraph/graphicsItems/PlotItem/PlotItem.py#L133 # noqa: E501
        # whenever something changes, we check whether to show "auto scale" button
        self.plotItem.vb.sigStateChanged.connect(
            self.check_whether_to_show_reset_view_button
        )

        # user may zoom only as far out as there is still data
        # https://stackoverflow.com/questions/18868530/pyqtgraph-limit-zoom-to-upper-lower-bound-of-axes

        self.getViewBox().setLimits(xMin=0, xMax=2048, yMin=-1, yMax=1)

        # NOTE: increasing the pen width requires OpenGL, otherwise painting gets
        # horribly slow. See: https://github.com/pyqtgraph/pyqtgraph/issues/533
        # OpenGL is enabled in the beginning of this file.
        # NOTE: OpenGL has a bug that causes the plot to be way too small. Therefore,
        # self.resize() is called below.

        self.crosshair = pg.InfiniteLine(pos=N_POINTS / 2, pen=pg.mkPen("w", width=1))
        self.addItem(self.crosshair)

        self.zero_line = pg.PlotCurveItem(pen=pg.mkPen("w", width=1))
        self.addItem(self.zero_line)
        self.signal_strength_a = pg.PlotCurveItem()
        self.addItem(self.signal_strength_a)
        self.signal_strength_a2 = pg.PlotCurveItem()
        self.addItem(self.signal_strength_a2)
        self.signal_strength_a_fill = pg.FillBetweenItem(
            self.signal_strength_a, self.signal_strength_a2
        )
        self.addItem(self.signal_strength_a_fill)
        self.signal_strength_b = pg.PlotCurveItem()
        self.addItem(self.signal_strength_b)
        self.signal_strength_b2 = pg.PlotCurveItem()
        self.addItem(self.signal_strength_b2)
        self.signal_strength_b_fill = pg.FillBetweenItem(
            self.signal_strength_b, self.signal_strength_b2
        )
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
        self.monitor_signal_history = pg.PlotCurveItem()
        self.addItem(self.monitor_signal_history)

        self.zero_line.setData([0, N_POINTS - 1], [0, 0])
        self.signal1.setData([0, N_POINTS - 1], [1, 1])
        self.signal1.setData([0, N_POINTS - 1], [1, 1])
        self.combined_signal.setData([0, N_POINTS - 1], [1, 1])

        self.connection = None
        self.parameters = None
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

        self.last_plot_time = 0
        self.plot_rate_limit = DEFAULT_PLOT_RATE_LIMIT

        self._plot_paused = False
        self._cached_plot_data = []
        self._should_reposition_reset_view_button = False

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        def set_pens(*args):
            pen_width = self.app.settings.plot_line_width.value

            for curve, color in {
                self.signal1: Color.SPECTRUM1,
                self.signal2: Color.SPECTRUM2,
                self.combined_signal: Color.SPECTRUM_COMBINED,
                self.control_signal: Color.CONTROL_SIGNAL,
                self.control_signal_history: Color.CONTROL_SIGNAL_HISTORY,
                self.slow_history: Color.SLOW_HISTORY,
                self.monitor_signal_history: Color.MONITOR_SIGNAL_HISTORY,
            }.items():
                r, g, b, _ = getattr(
                    self.app.settings, f"plot_color_{color.value}"
                ).value
                a = self.app.settings.plot_line_opacity.value
                curve.setPen(pg.mkPen((r, g, b, a), width=pen_width))

        for color_idx in range(N_COLORS):
            getattr(self.app.settings, f"plot_color_{color_idx}").add_callback(set_pens)
        self.app.settings.plot_line_width.add_callback(set_pens)
        self.app.settings.plot_line_opacity.add_callback(set_pens)

        self.control_signal_history_data = self.parameters.control_signal_history.value
        self.monitor_signal_history_data = self.parameters.monitor_signal_history.value

        self.parameters.to_plot.add_callback(self.replot)

        def autolock_selection_changed(value):
            if value:
                self.parameters.optimization_selection.value = False
                self.enable_area_selection(selectable_width=0.99)
                self.pause_plot_and_cache_data()
            elif not self.parameters.optimization_selection.value:
                self.disable_area_selection()
                self.resume_plot_and_clear_cache()

        self.parameters.autolock_selection.add_callback(autolock_selection_changed)

        def optimization_selection_changed(value):
            if value:
                self.parameters.autolock_selection.value = False
                self.enable_area_selection(selectable_width=0.75)
                self.pause_plot_and_cache_data()
            elif not self.parameters.autolock_selection.value:
                self.disable_area_selection()
                self.resume_plot_and_clear_cache()

        self.parameters.optimization_selection.add_callback(
            optimization_selection_changed
        )

        def show_or_hide_crosshair(automatic_mode):
            self.crosshair.setVisible(not automatic_mode)

        self.parameters.automatic_mode.add_callback(show_or_hide_crosshair)

    def _to_data_coords(self, event):
        pos = self.plotItem.vb.mapSceneToView(event.pos())
        x, y = pos.x(), pos.y()
        return x, y

    def mouseMoveEvent(self, event):
        if not self.selection_running:
            super().mouseMoveEvent(event)
        else:
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

        if self.selection_running:
            if event.button() == QtCore.Qt.RightButton:
                return

            x, y = self._to_data_coords(event)

            if self.selection_running:
                if x < self.selection_boundaries[0] or x > self.selection_boundaries[1]:
                    return

            self.touch_start = x, y
            self.set_selection_overlay(x, 0)
            self.overlay.setVisible(True)

    def _within_boundaries(self, x):
        boundaries = (
            self.selection_boundaries if self.selection_running else [0, N_POINTS]
        )

        if x < boundaries[0]:
            return boundaries[0]
        if x > boundaries[1]:
            return boundaries[1]
        return x

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if self.selection_running:
            if self.touch_start is None:
                return

            x, y = self._to_data_coords(event)
            x = self._within_boundaries(x)
            x0, y0 = self.touch_start
            xdiff = np.abs(x0 - x)
            xmax = len(self.last_plot_data[0]) - 1
            if xdiff / xmax < 0.01:
                # it was a click
                pass
            else:
                # it was a selection
                if self.selection_running:
                    if self.parameters.autolock_selection.value:
                        last_combined_error_signal = self.last_plot_data[2]
                        self.parameters.autolock_selection.value = False

                        self.control.start_autolock(
                            # we pickle it here because otherwise a netref is
                            # transmitted which blocks the autolock
                            *sorted([x0, x]),
                            pickle.dumps(last_combined_error_signal),
                            additional_spectra=pickle.dumps(self._cached_plot_data),
                        )

                        (
                            mean_signal,
                            target_slope_rising,
                            target_zoom,
                            rolled_error_signal,
                            line_width,
                            peak_idxs,
                        ) = get_lock_point(
                            last_combined_error_signal, *sorted((int(x0), int(x)))
                        )
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

    def replot(self, to_plot):
        time_beginning = time()

        if self._should_reposition_reset_view_button:
            self._should_reposition_reset_view_button = False
            self.position_reset_view_button()

        if (
            time_beginning - self.last_plot_time <= self.plot_rate_limit
            and not self._plot_paused
        ):
            # don't plot too often as it only causes unnecessary load this does not
            # apply if plot is paused, because in this case we want to collect all the
            # data that we can get in order to pass it to the autolock
            return

        self.last_plot_time = time_beginning

        # NOTE: this is necessary if OpenGL is activated. Otherwise, the plot is way too
        # small. This command apparently causes a repaint and works fine even though the
        # values are nonsense.
        if not self._fixed_opengl_bug:
            self._fixed_opengl_bug = True
            self.resize(
                self.parent().frameGeometry().width(),
                self.parent().frameGeometry().height(),
            )

        if self.parameters.pause_acquisition.value:
            return

        if to_plot is not None:
            to_plot = pickle.loads(to_plot)

            if to_plot is None:
                return

            if not check_plot_data(self.parameters.lock.value, to_plot):
                return

            # we also call this if the laser is not locked because it resets the history
            # in this case
            history, slow_history = self.update_signal_history(to_plot)

            if self.parameters.lock.value:
                self.signal1.setVisible(False)
                self.signal2.setVisible(False)
                self.control_signal.setVisible(True)
                self.control_signal_history.setVisible(True)
                self.slow_history.setVisible(self.parameters.pid_on_slow_enabled.value)
                self.monitor_signal_history.setVisible(
                    not self.parameters.dual_channel.value
                )
                self.combined_signal.setVisible(True)
                self.signal_strength_a.setVisible(False)
                self.signal_strength_b.setVisible(False)
                self.signal_strength_a2.setVisible(False)
                self.signal_strength_b2.setVisible(False)
                self.signal_strength_a_fill.setVisible(False)
                self.signal_strength_b_fill.setVisible(False)

                error_signal, control_signal = (
                    to_plot["error_signal"],
                    to_plot["control_signal"],
                )
                all_signals = (error_signal, control_signal, history, slow_history)

                self.plot_data_locked(to_plot)
                self.plot_autolock_target_line(None)
            else:
                dual_channel = self.parameters.dual_channel.value
                self.signal1.setVisible(True)
                monitor_signal = to_plot.get("monitor_signal")
                error_signal_2 = to_plot.get("error_signal_2")
                self.signal2.setVisible(
                    error_signal_2 is not None or monitor_signal is not None
                )
                self.combined_signal.setVisible(dual_channel)
                self.control_signal.setVisible(False)
                self.control_signal_history.setVisible(False)
                self.slow_history.setVisible(False)
                self.monitor_signal_history.setVisible(False)

                s1 = to_plot["error_signal_1"]
                s2 = error_signal_2 if error_signal_2 is not None else monitor_signal

                combined_error_signal = combine_error_signal(
                    (s1, s2),
                    dual_channel,
                    self.parameters.channel_mixing.value,
                    self.parameters.combined_offset.value,
                )

                if self._plot_paused:
                    self._cached_plot_data.append(combined_error_signal)
                    # don't save too much
                    self._cached_plot_data = self._cached_plot_data[-20:]
                    return

                all_signals = [s1, s2] + [combined_error_signal]
                self.last_plot_data = all_signals

                self.plot_data_unlocked((s1, s2), combined_error_signal)
                self.plot_autolock_target_line(combined_error_signal)

                if (self.parameters.modulation_frequency.value != 0) and (
                    not self.parameters.pid_only_mode.value
                ):
                    # check whether to plot signal strengths using quadratures
                    s1q = to_plot.get("error_signal_1_quadrature")
                    s2q = to_plot.get("error_signal_2_quadrature")

                    self.signal_strength_a.setVisible(s1q is not None)
                    self.signal_strength_a2.setVisible(s1q is not None)
                    self.signal_strength_a_fill.setVisible(s1q is not None)

                    self.signal_strength_b.setVisible(s2q is not None)
                    self.signal_strength_b2.setVisible(s2q is not None)
                    self.signal_strength_b_fill.setVisible(s2q is not None)

                    if s1q is not None:
                        max_signal_strength_V = (
                            self.plot_signal_strength(
                                s1,
                                s1q,
                                self.signal_strength_a,
                                self.signal_strength_a2,
                                self.signal_strength_a_fill,
                                self.parameters.offset_a.value,
                                self.app.settings.plot_color_0.value,
                            )
                            / V
                        )
                        all_signals.append(
                            [
                                max_signal_strength_V * V,
                                -1 * max_signal_strength_V * V,
                            ]
                        )

                        self.signal_power1.emit(
                            peak_voltage_to_dBm(max_signal_strength_V)
                        )
                    else:
                        self.signal_power1.emit(INVALID_POWER)

                    if s2q is not None:
                        max_signal_strength2_V = (
                            self.plot_signal_strength(
                                s2,
                                s2q,
                                self.signal_strength_b,
                                self.signal_strength_b2,
                                self.signal_strength_b_fill,
                                self.parameters.offset_b.value,
                                self.app.settings.plot_color_1.value,
                            )
                            / V
                        )

                        all_signals.append(
                            [
                                max_signal_strength2_V * V,
                                -1 * max_signal_strength2_V * V,
                            ]
                        )

                        self.signal_power2.emit(
                            peak_voltage_to_dBm(max_signal_strength2_V)
                        )
                    else:
                        self.signal_power2.emit(INVALID_POWER)
                else:
                    self.signal_strength_a.setVisible(False)
                    self.signal_strength_b.setVisible(False)
                    self.signal_strength_a2.setVisible(False)
                    self.signal_strength_b2.setVisible(False)
                    self.signal_strength_a_fill.setVisible(False)
                    self.signal_strength_b_fill.setVisible(False)

                    self.signal_power1.emit(INVALID_POWER)
                    self.signal_power2.emit(INVALID_POWER)

        time_end = time()
        time_diff = time_end - time_beginning
        new_rate_limit = 2 * time_diff

        if new_rate_limit < DEFAULT_PLOT_RATE_LIMIT:
            new_rate_limit = DEFAULT_PLOT_RATE_LIMIT

        self.plot_rate_limit = new_rate_limit

    def plot_signal_strength(
        self, i, q, signal, neg_signal, fill, channel_offset, color
    ):
        # we have to subtract channel offset here and will add it back in the end
        i -= int(round(channel_offset))
        q -= int(round(channel_offset))
        signal_strength = get_signal_strength_from_i_q(i, q)

        r, g, b, *stuff = color

        x = list(range(len(signal_strength)))
        signal_strength_scaled = signal_strength / V
        upper = (channel_offset / V) + signal_strength_scaled
        lower = (channel_offset / V) - 1 * signal_strength_scaled

        brush = pg.mkBrush(r, g, b, self.app.settings.plot_fill_opacity.value)
        fill.setBrush(brush)

        invisible_pen = pg.mkPen("k", width=0.00001)
        signal.setData(x, upper, pen=invisible_pen)
        neg_signal.setData(x, lower, pen=invisible_pen)
        return np.max([np.max(upper), -1 * np.min(lower)]) * V

    def plot_data_unlocked(self, error_signals, combined_signal):
        error_signal1, error_signal2 = error_signals
        self.signal1.setData(list(range(len(error_signal1))), error_signal1 / V)
        self.signal2.setData(list(range(len(error_signal2))), error_signal2 / V)
        self.combined_signal.setData(
            list(range(len(combined_signal))), combined_signal / V
        )

    def plot_data_locked(self, signals):
        error_signal = signals["error_signal"]
        control_signal = signals["control_signal"]
        self.combined_signal.setData(list(range(len(error_signal))), error_signal / V)
        self.control_signal.setData(list(range(len(error_signal))), control_signal / V)

    def plot_autolock_target_line(self, combined_error_signal):
        if (
            self.autolock_ref_spectrum is not None
            and self.parameters.autolock_preparing.value
        ):
            sweep_amplitude = self.parameters.sweep_amplitude.value
            zoom_factor = 1 / sweep_amplitude
            initial_zoom_factor = (
                1 / self.parameters.autolock_initial_sweep_amplitude.value
            )

            try:
                shift, _1, _2 = determine_shift_by_correlation(
                    zoom_factor / initial_zoom_factor,
                    self.autolock_ref_spectrum,
                    combined_error_signal,
                )
                shift *= zoom_factor / initial_zoom_factor
                length = len(combined_error_signal)
                shift = (length / 2) - (shift / 2 * length)

                self.lock_target_line.setVisible(True)
                self.lock_target_line.setValue(shift)

            except SpectrumUncorrelatedException:
                self.lock_target_line.setVisible(False)
        else:
            self.lock_target_line.setVisible(False)

    def keyPressEvent(self, event):
        # we listen here in addition to the main window because some events are only
        # caught here
        self.keyPressed.emit(event.key())

    def update_signal_history(self, to_plot):
        update_signal_history(
            self.control_signal_history_data,
            self.monitor_signal_history_data,
            to_plot,
            self.parameters.lock.value,
            self.parameters.control_signal_history_length.value,
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

            history = self.control_signal_history_data["values"]
            self.control_signal_history.setData(
                scale(self.control_signal_history_data["times"]), np.array(history) / V
            )

            slow_values = self.control_signal_history_data["slow_values"]
            self.slow_history.setData(
                scale(self.control_signal_history_data["slow_times"]),
                np.array(slow_values) / V,
            )

            if not self.parameters.dual_channel.value:
                self.monitor_signal_history.setData(
                    scale(self.monitor_signal_history_data["times"]),
                    np.array(self.monitor_signal_history_data["values"]) / V,
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
        self.boundary_overlays[1].setRegion(
            (x_axis_length - boundary_width, x_axis_length + extra_width)
        )

        for overlay in self.boundary_overlays:
            overlay.setVisible(True)

    def disable_area_selection(self):
        self.selection_running = False

        for overlay in self.boundary_overlays:
            overlay.setVisible(False)

    def pause_plot_and_cache_data(self):
        """This function pauses plot updates. All incoming data is cached though.
        This is useful for letting the user select a line that is then used in
        the autolock."""
        self._plot_paused = True

    def resume_plot_and_clear_cache(self):
        """Resumes plotting again."""
        self._plot_paused = False
        self._cached_plot_data = []

    def init_reset_view_button(self):
        self.reset_view_button = QtWidgets.QPushButton(self)
        self.reset_view_button.setText("Reset view")
        self.reset_view_button.setStyleSheet("padding: 10px; font-weight: bold")
        icon = QtGui.QIcon.fromTheme("view-restore")
        self.reset_view_button.setIcon(icon)
        self.reset_view_button.clicked.connect(self.reset_view)
        self.position_reset_view_button()

    # called when widget is resized
    def position_reset_view_button(self):
        pos = QtCore.QPoint(
            self.geometry().width() - self.reset_view_button.geometry().width() - 25,
            25,
        )
        self.reset_view_button.move(pos)

    def check_whether_to_show_reset_view_button(self):
        # copied from https://github.com/pyqtgraph/pyqtgraph/blob/master/pyqtgraph/graphicsItems/PlotItem/PlotItem.py#L1195 # noqa: E501
        auto_scale_disabled = not all(self.plotItem.vb.autoRangeEnabled())
        if auto_scale_disabled:
            self.reset_view_button.show()
        else:
            self.reset_view_button.hide()

    def reset_view(self):
        self.enableAutoRange()

    def resizeEvent(self, event, *args, **kwargs):
        super().resizeEvent(event, *args, **kwargs)

        # we don't do it directly here because this causes problems for some reason
        self._should_reposition_reset_view_button = True
