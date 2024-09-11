# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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
from time import time

import numpy as np
import pyqtgraph as pg
from linien_common.common import (
    DECIMATION,
    N_POINTS,
    check_plot_data,
    combine_error_signal,
    get_lock_point,
    get_signal_strength_from_i_q,
    update_signal_history,
)
from linien_gui.config import DEFAULT_PLOT_RATE_LIMIT
from linien_gui.utils import get_linien_app_instance
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal
from pyqtgraph.Qt import QtCore

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
VOLTS_TO_COUNTS_FACTOR = 8192

# pyqt signals enforce type, so...
INVALID_POWER = -1000


def peak_voltage_to_dBm(voltage):
    return 10 + 20 * np.log10(voltage)


class TimeXAxis(pg.AxisItem):
    """Plot x axis as time in seconds instead of point number."""

    def __init__(self, *args, parent=None, **kwargs):
        self.parent = parent
        pg.AxisItem.__init__(self, *args, **kwargs)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

    def on_connection_established(self):
        # we have to wait until parameters (of parent) is available
        QtCore.QTimer.singleShot(100, self.listen_to_parameter_changes)

    def listen_to_parameter_changes(self):
        self.parent.parameters.sweep_center.add_callback(self.on_lock_changed)
        self.parent.parameters.sweep_amplitude.add_callback(self.on_lock_changed)
        self.parent.parameters.lock.add_callback(self.on_lock_changed)
        self.on_lock_changed()

    def tickStrings(self, values, scale, spacing) -> list[str]:
        if self.parent.parameters.lock.value:
            # use µs for the x axis
            spacing = DECIMATION / 125e6
            values = [1e6 * scale * v * spacing for v in values]
            precision_specifier = 1
        else:
            # use voltage for the x axis
            center = self.parent.parameters.sweep_center.value
            amplitude = self.parent.parameters.sweep_amplitude.value
            min_ = center - amplitude
            max_ = center + amplitude
            spacing = abs(max_ - min_) / (N_POINTS - 1)
            values = [scale * (v * spacing + min_) for v in values]
            precision_specifier = 2
        return [f"{v:.{precision_specifier}f}" for v in values]

    def on_lock_changed(self, *args) -> None:
        self.picture = None
        self.update()


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

        self.touch_start = None
        self.autolock_ref_spectrum = None
        self.selection_running = False
        self.selection_boundaries = None
        self.autolock_selection_running = False
        self.optimization_selection_running = False

        self.getAxis("bottom").enableAutoSIPrefix(False)
        self.showGrid(x=True, y=True)

        # Causes auto-scale button (‘A’ in lower-left corner) to be hidden for this
        # PlotItem
        self.hideButtons()
        # we have our own "reset view" button instead
        self.reset_view_button = QtWidgets.QPushButton(self)
        self.reset_view_button.setText("Reset view")
        self.reset_view_button.setStyleSheet("padding: 10px; font-weight: bold")
        icon = QtGui.QIcon.fromTheme("view-restore")
        self.reset_view_button.setIcon(icon)
        self.reset_view_button.clicked.connect(self.reset_view)
        self.position_reset_view_button()

        # copied from https://github.com/pyqtgraph/pyqtgraph/blob/master/pyqtgraph/graphicsItems/PlotItem/PlotItem.py#L133 # noqa: E501
        # whenever something changes, we check whether to show "auto scale" button
        self.plotItem.vb.sigStateChanged.connect(
            self.check_whether_to_show_reset_view_button
        )

        # user may zoom only as far out as there is still data
        # https://stackoverflow.com/questions/18868530/pyqtgraph-limit-zoom-to-upper-lower-bound-of-axes

        self.getViewBox().setLimits(xMin=0, xMax=2048, yMin=-1.05, yMax=1.05)

        # NOTE: increasing the pen width requires OpenGL, otherwise painting gets
        # horribly slow. See: https://github.com/pyqtgraph/pyqtgraph/issues/533
        # OpenGL is enabled in the beginning of this file.
        # NOTE: OpenGL has a bug that causes the plot to be way too small. Therefore,
        # self.resize() is called below.
        self.crosshair = pg.InfiniteLine(pos=N_POINTS / 2, pen=pg.mkPen("w", width=1))
        self.addItem(self.crosshair)

        self.zeroLine = pg.PlotCurveItem(pen=pg.mkPen("w", width=1))
        self.addItem(self.zeroLine)
        self.signalStrengthA = pg.PlotCurveItem()
        self.addItem(self.signalStrengthA)
        self.signalStrengthA2 = pg.PlotCurveItem()
        self.addItem(self.signalStrengthA2)
        self.signalStrengthAFill = pg.FillBetweenItem(
            self.signalStrengthA, self.signalStrengthA2
        )
        self.addItem(self.signalStrengthAFill)
        self.signalStrengthB = pg.PlotCurveItem()
        self.addItem(self.signalStrengthB)
        self.signalStrengthB2 = pg.PlotCurveItem()
        self.addItem(self.signalStrengthB2)
        self.signalStrengthBFill = pg.FillBetweenItem(
            self.signalStrengthB, self.signalStrengthB2
        )
        self.addItem(self.signalStrengthBFill)
        self.errorSignal1 = pg.PlotCurveItem()
        self.addItem(self.errorSignal1)
        self.errorSignal2 = pg.PlotCurveItem()
        self.addItem(self.errorSignal2)
        self.combinedErrorSignal = pg.PlotCurveItem()
        self.addItem(self.combinedErrorSignal)
        self.monitorSignal = pg.PlotCurveItem()
        self.addItem(self.monitorSignal)

        self.controlSignal = pg.PlotCurveItem()
        self.addItem(self.controlSignal)
        self.controlSignalHistory = pg.PlotCurveItem()
        self.addItem(self.controlSignalHistory)
        self.slowHistory = pg.PlotCurveItem()
        self.addItem(self.slowHistory)
        self.monitorSignalHistory = pg.PlotCurveItem()
        self.addItem(self.monitorSignalHistory)

        self.zeroLine.setData([0, N_POINTS - 1], [0, 0])
        self.errorSignal1.setData([0, N_POINTS - 1], [1, 1])
        self.errorSignal1.setData([0, N_POINTS - 1], [1, 1])
        self.combinedErrorSignal.setData([0, N_POINTS - 1], [1, 1])

        # these lines are used for configuration of the relocking system
        self.control_signal_threshold_min = pg.InfiniteLine(angle=90)
        self.addItem(self.control_signal_threshold_min)
        self.control_signal_threshold_max = pg.InfiniteLine(angle=90)
        self.addItem(self.control_signal_threshold_max)
        self.error_signal_threshold_min = pg.InfiniteLine(angle=0)
        self.addItem(self.error_signal_threshold_min)
        self.error_signal_threshold_max = pg.InfiniteLine(angle=0)
        self.addItem(self.error_signal_threshold_max)
        self.monitor_signal_threshold_min = pg.InfiniteLine(angle=0)
        self.addItem(self.monitor_signal_threshold_min)
        self.monitor_signal_threshold_max = pg.InfiniteLine(angle=0)
        self.addItem(self.monitor_signal_threshold_max)

        self.overlay = pg.LinearRegionItem(values=(0, 0), movable=False)
        self.overlay.setVisible(False)
        self.addItem(self.overlay)

        self.boundary_overlays = [
            pg.LinearRegionItem(values=(0, 0), movable=False, brush=(0, 0, 0, 200))
            for _ in range(2)
        ]
        for i, overlay in enumerate(self.boundary_overlays):
            overlay.setVisible(False)
            # make outer borders invisible, see
            # https://github.com/pyqtgraph/pyqtgraph/issues/462
            overlay.lines[i].setPen((0, 0, 0, 0))
            self.addItem(overlay)

        self._fixed_opengl_bug = False

        self.last_plot_time = 0
        self.plot_rate_limit = DEFAULT_PLOT_RATE_LIMIT

        self.plot_paused = False
        self.cached_plot_data = []
        self._should_reposition_reset_view_button = False

        for plot_color_setting in self.app.settings.plot_colors:
            plot_color_setting.add_callback(self.on_plot_settings_changed)
        self.app.settings.plot_line_width.add_callback(self.on_plot_settings_changed)
        self.app.settings.plot_line_opacity.add_callback(self.on_plot_settings_changed)

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        self.control_signal_history_data = self.parameters.control_signal_history.value
        self.monitor_signal_history_data = self.parameters.monitor_signal_history.value
        self.parameters.to_plot.add_callback(self.on_new_plot_data_received)
        self.parameters.automatic_mode.add_callback(self.on_automatic_mode_changed)
        self.parameters.lock.add_callback(self.on_lock_changed)

    def _to_data_coords(self, event):
        pos = self.plotItem.vb.mapSceneToView(event.pos())
        x, y = pos.x(), pos.y()
        return x, y

    def _within_boundaries(self, x):
        boundaries = (
            self.selection_boundaries if self.selection_running else [0, N_POINTS]
        )

        if x < boundaries[0]:
            return boundaries[0]
        if x > boundaries[1]:
            return boundaries[1]
        return x

    def keyPressEvent(self, event):
        # we listen here in addition to the main window because some events are only
        # caught here
        self.keyPressed.emit(event.key())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.selection_running:
            if event.button() == QtCore.Qt.RightButton:
                return
            x, y = self._to_data_coords(event)
            if x < self.selection_boundaries[0] or x > self.selection_boundaries[1]:
                return
            self.touch_start = x, y
            self.overlay.setRegion((x, x))
            self.overlay.setVisible(True)

    def mouseMoveEvent(self, event):
        if not self.selection_running:
            super().mouseMoveEvent(event)
        else:
            if self.touch_start is None:
                return
            x0, y0 = self.touch_start
            x, y = self._to_data_coords(event)
            x = self._within_boundaries(x)
            self.overlay.setRegion((x0, x))

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
            if xdiff / xmax < 0.01:  # it was a click
                pass
            else:  # it was a selection
                if self.autolock_selection_running:
                    last_combined_error_signal = self.last_plot_data[2]
                    self.autolock_selection_running = False
                    self.control.exposed_start_autolock(
                        # we pickle it here because otherwise a netref is
                        # transmitted which blocks the autolock
                        *sorted([x0, x]),
                        pickle.dumps(last_combined_error_signal),
                        additional_spectra=pickle.dumps(self.cached_plot_data),
                    )
                    (_, _, _, rolled_error_signal, _, _) = get_lock_point(
                        last_combined_error_signal, *sorted((int(x0), int(x)))
                    )
                    self.autolock_ref_spectrum = rolled_error_signal
                elif self.optimization_selection_running:
                    spectrum = self.last_plot_data[
                        (
                            0
                            if not self.parameters.dual_channel.value
                            else (0, 1)[self.parameters.optimization_channel.value]
                        )
                    ]
                    self.optimization_selection_running = False
                    points = sorted([int(x0), int(x)])
                    self.control.exposed_start_optimization(
                        *points, pickle.dumps(spectrum)
                    )
            self.overlay.setVisible(False)
            self.touch_start = None

    def on_plot_settings_changed(self, _) -> None:
        pen_width = self.app.settings.plot_line_width.value
        opacity = self.app.settings.plot_line_opacity.value
        for curve, color in {
            self.combinedErrorSignal: self.app.settings.plot_color_error_combined,
            self.errorSignal1: self.app.settings.plot_color_error1,
            self.errorSignal2: self.app.settings.plot_color_error2,
            self.monitorSignal: self.app.settings.plot_color_monitor,
            self.monitorSignalHistory: self.app.settings.plot_color_monitor_history,
            self.controlSignal: self.app.settings.plot_color_control,
            self.controlSignalHistory: self.app.settings.plot_color_control_history,
            self.slowHistory: self.app.settings.plot_color_slow_control,
        }.items():
            curve.setPen(pg.mkPen((*color.value, opacity), width=pen_width))

        for line, color in {
            self.control_signal_threshold_min: self.app.settings.plot_color_control,
            self.control_signal_threshold_max: self.app.settings.plot_color_control,
            self.error_signal_threshold_min: self.app.settings.plot_color_error_combined,  # noqa: E501
            self.error_signal_threshold_max: self.app.settings.plot_color_error_combined,  # noqa: E501
            self.monitor_signal_threshold_min: self.app.settings.plot_color_monitor,
            self.monitor_signal_threshold_max: self.app.settings.plot_color_monitor,
        }.items():
            line.setPen(
                pg.mkPen(
                    (*color.value, opacity), width=pen_width, style=QtCore.Qt.DashLine
                )
            )

    def on_autolock_selection_changed(self, value: bool) -> None:
        if value:
            self.autolock_selection_running = True
            self.optimization_selection_running = False
            self.enable_area_selection(selectable_width=0.99)
            self.pause_plot()
        else:
            self.autolock_selection_running = False
            self.disable_area_selection()
            self.resume_plot_and_clear_cache()

    def on_optimization_selection_changed(self, value: bool) -> None:
        if value:
            self.optimization_selection_running = True
            self.autolock_selection_running = False
            self.enable_area_selection(selectable_width=0.75)
            self.pause_plot()
        else:
            self.optimization_selection_running = False
            self.disable_area_selection()
            self.resume_plot_and_clear_cache()

    def on_automatic_mode_changed(self, automatic_mode: bool) -> None:
        """Show or hide crosshair"""
        self.crosshair.setVisible(not automatic_mode)

    def on_lock_changed(self, lock: bool) -> None:
        if not lock:
            self.setLabel("bottom", "sweep voltage", units="V")
        else:
            self.setLabel("bottom", "time", units="µs")

    def on_new_plot_data_received(self, to_plot):
        time_beginning = time()

        if self._should_reposition_reset_view_button:
            self._should_reposition_reset_view_button = False
            self.position_reset_view_button()

        if (
            time_beginning - self.last_plot_time <= self.plot_rate_limit
            and not self.plot_paused
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
            update_signal_history(
                self.control_signal_history_data,
                self.monitor_signal_history_data,
                to_plot,
                self.parameters.lock.value,
                self.parameters.control_signal_history_length.value,
            )

            if self.parameters.lock.value:
                dual_channel = self.parameters.dual_channel.value
                timescale = self.parameters.control_signal_history_length.value

                self.errorSignal1.setVisible(False)
                self.errorSignal2.setVisible(False)
                self.monitorSignal.setVisible(False)
                self.signalStrengthA.setVisible(False)
                self.signalStrengthB.setVisible(False)
                self.signalStrengthA2.setVisible(False)
                self.signalStrengthB2.setVisible(False)
                self.signalStrengthAFill.setVisible(False)
                self.signalStrengthBFill.setVisible(False)

                self.combinedErrorSignal.setVisible(True)
                self.combinedErrorSignal.setData(
                    list(range(len(to_plot["error_signal"]))),
                    to_plot["error_signal"] / VOLTS_TO_COUNTS_FACTOR,
                )

                self.controlSignal.setVisible(True)
                self.controlSignal.setData(
                    list(range(len(to_plot["control_signal"]))),
                    to_plot["control_signal"] / VOLTS_TO_COUNTS_FACTOR,
                )

                self.controlSignalHistory.setVisible(True)
                self.controlSignalHistory.setData(
                    scale_history_times(
                        self.control_signal_history_data["times"], timescale
                    ),
                    np.array(self.control_signal_history_data["values"])
                    / VOLTS_TO_COUNTS_FACTOR,
                )

                self.slowHistory.setVisible(self.parameters.pid_on_slow_enabled.value)
                self.slowHistory.setData(
                    scale_history_times(
                        self.control_signal_history_data["slow_times"], timescale
                    ),
                    np.array(self.control_signal_history_data["slow_values"])
                    / VOLTS_TO_COUNTS_FACTOR,
                )

                self.monitorSignalHistory.setVisible(not dual_channel)
                if not dual_channel:
                    self.monitorSignalHistory.setData(
                        scale_history_times(
                            self.monitor_signal_history_data["times"], timescale
                        ),
                        np.array(self.monitor_signal_history_data["values"])
                        / VOLTS_TO_COUNTS_FACTOR,
                    )
            else:
                dual_channel = self.parameters.dual_channel.value
                monitor_signal = to_plot.get("monitor_signal")
                error_signal_2 = to_plot.get("error_signal_2")
                error_signal_1 = to_plot["error_signal_1"]
                monitor_or_error_signal_2 = (
                    error_signal_2 if error_signal_2 is not None else monitor_signal
                )

                combined_error_signal = combine_error_signal(
                    (error_signal_1, monitor_or_error_signal_2),
                    dual_channel,
                    self.parameters.channel_mixing.value,
                    self.parameters.combined_offset.value if dual_channel else 0,
                )

                if self.plot_paused:
                    self.cached_plot_data.append(combined_error_signal)
                    # don't save too much
                    self.cached_plot_data = self.cached_plot_data[-20:]
                    return

                self.last_plot_data = [error_signal_1, monitor_or_error_signal_2] + [
                    combined_error_signal
                ]

                self.controlSignal.setVisible(False)
                self.controlSignalHistory.setVisible(False)
                self.slowHistory.setVisible(False)
                self.monitorSignalHistory.setVisible(False)

                self.combinedErrorSignal.setVisible(True)
                self.combinedErrorSignal.setData(
                    list(range(len(error_signal_1))),
                    error_signal_1 / VOLTS_TO_COUNTS_FACTOR,
                )

                self.errorSignal1.setVisible(dual_channel)
                if error_signal_1 is not None:
                    self.errorSignal1.setData(
                        list(range(len(error_signal_1))),
                        error_signal_1 / VOLTS_TO_COUNTS_FACTOR,
                    )

                self.errorSignal2.setVisible(dual_channel)
                if error_signal_2 is not None:
                    self.errorSignal2.setData(
                        list(range(len(error_signal_2))),
                        error_signal_2 / VOLTS_TO_COUNTS_FACTOR,
                    )

                self.monitorSignal.setVisible(not dual_channel)
                if monitor_signal is not None:
                    self.monitorSignal.setData(
                        list(range(len(monitor_signal))),
                        monitor_signal / VOLTS_TO_COUNTS_FACTOR,
                    )

                if (self.parameters.modulation_frequency.value != 0) and (
                    not self.parameters.pid_only_mode.value
                ):
                    # check whether to plot signal strengths using quadratures
                    error_1_quadrature = to_plot.get("error_signal_1_quadrature")
                    error_2_quadrature = to_plot.get("error_signal_2_quadrature")

                    self.signalStrengthA.setVisible(error_1_quadrature is not None)
                    self.signalStrengthA2.setVisible(error_1_quadrature is not None)
                    self.signalStrengthAFill.setVisible(error_1_quadrature is not None)
                    self.signalStrengthB.setVisible(error_2_quadrature is not None)
                    self.signalStrengthB2.setVisible(error_2_quadrature is not None)
                    self.signalStrengthBFill.setVisible(error_2_quadrature is not None)

                    if error_1_quadrature is not None:

                        if self.parameters.dual_channel.value:
                            color = self.app.settings.plot_color_error1
                        else:
                            color = self.app.settings.plot_color_error_combined
                        max_signal_strength_V = (
                            self.plot_signal_strength(
                                error_signal_1,
                                error_1_quadrature,
                                self.signalStrengthA,
                                self.signalStrengthA2,
                                self.signalStrengthAFill,
                                self.parameters.offset_a.value,
                                color.value,
                            )
                            / VOLTS_TO_COUNTS_FACTOR
                        )

                        self.signal_power1.emit(
                            peak_voltage_to_dBm(max_signal_strength_V)
                        )
                    else:
                        self.signal_power1.emit(INVALID_POWER)

                    if error_2_quadrature is not None:
                        max_signal_strength2_V = (
                            self.plot_signal_strength(
                                monitor_or_error_signal_2,
                                error_2_quadrature,
                                self.signalStrengthB,
                                self.signalStrengthB2,
                                self.signalStrengthBFill,
                                self.parameters.offset_b.value,
                                self.app.settings.plot_color_error2.value,
                            )
                            / VOLTS_TO_COUNTS_FACTOR
                        )

                        self.signal_power2.emit(
                            peak_voltage_to_dBm(max_signal_strength2_V)
                        )
                    else:
                        self.signal_power2.emit(INVALID_POWER)
                else:
                    self.signalStrengthA.setVisible(False)
                    self.signalStrengthB.setVisible(False)
                    self.signalStrengthA2.setVisible(False)
                    self.signalStrengthB2.setVisible(False)
                    self.signalStrengthAFill.setVisible(False)
                    self.signalStrengthBFill.setVisible(False)

                    self.signal_power1.emit(INVALID_POWER)
                    self.signal_power2.emit(INVALID_POWER)

        time_end = time()
        time_diff = time_end - time_beginning
        new_rate_limit = 2 * time_diff

        if new_rate_limit < DEFAULT_PLOT_RATE_LIMIT:
            new_rate_limit = DEFAULT_PLOT_RATE_LIMIT

        self.plot_rate_limit = new_rate_limit

    def plot_signal_strength(
        self,
        i,
        q,
        signal,
        neg_signal,
        fill,
        channel_offset,
        color: tuple[int, int, int],
    ) -> float:
        # we have to subtract channel offset here and will add it back in the end
        i -= int(round(channel_offset))
        q -= int(round(channel_offset))
        signal_strength = get_signal_strength_from_i_q(i, q)

        x = list(range(len(signal_strength)))
        signal_strength_scaled = signal_strength / VOLTS_TO_COUNTS_FACTOR
        upper = (channel_offset / VOLTS_TO_COUNTS_FACTOR) + signal_strength_scaled
        lower = (channel_offset / VOLTS_TO_COUNTS_FACTOR) - 1 * signal_strength_scaled

        brush = pg.mkBrush(*color, self.app.settings.plot_fill_opacity.value)
        fill.setBrush(brush)

        invisible_pen = pg.mkPen("k", width=0.00001)
        signal.setData(x, upper, pen=invisible_pen)
        neg_signal.setData(x, lower, pen=invisible_pen)
        return np.max([np.max(upper), -1 * np.min(lower)]) * VOLTS_TO_COUNTS_FACTOR

    def plot_data_unlocked(self, error_signals, combined_signal):
        error_signal1, error_signal2 = error_signals
        self.signal1.setData(
            list(range(len(error_signal1))), error_signal1 / VOLTS_TO_COUNTS_FACTOR
        )
        self.signal2.setData(
            list(range(len(error_signal2))), error_signal2 / VOLTS_TO_COUNTS_FACTOR
        )
        self.combined_signal.setData(
            list(range(len(combined_signal))), combined_signal / VOLTS_TO_COUNTS_FACTOR
        )

    def plot_data_locked(self, signals):
        error_signal = signals["error_signal"]
        control_signal = signals["control_signal"]
        self.combined_signal.setData(
            list(range(len(error_signal))), error_signal / VOLTS_TO_COUNTS_FACTOR
        )
        self.control_signal.setData(
            list(range(len(error_signal))), control_signal / VOLTS_TO_COUNTS_FACTOR
        )

    def update_signal_history(self, to_plot):
        update_signal_history(
            self.control_signal_history_data,
            self.monitor_signal_history_data,
            to_plot,
            self.parameters.lock.value,
            self.parameters.control_signal_history_length.value,
        )

        if self.parameters.lock.value:

            def scale(arr):
                timescale = self.parameters.control_signal_history_length.value
                if arr:
                    arr = np.array(arr)
                    arr -= arr[0]
                    arr *= 1 / timescale * N_POINTS
                return arr

            history = self.control_signal_history_data["values"]
            self.control_signal_history.setData(
                scale(self.control_signal_history_data["times"]),
                np.array(history) / VOLTS_TO_COUNTS_FACTOR,
            )

            slow_values = self.control_signal_history_data["slow_values"]
            self.slow_history.setData(
                scale(self.control_signal_history_data["slow_times"]),
                np.array(slow_values) / VOLTS_TO_COUNTS_FACTOR,
            )

            if not self.parameters.dual_channel.value:
                self.monitor_signal_history.setData(
                    scale(self.monitor_signal_history_data["times"]),
                    np.array(self.monitor_signal_history_data["values"])
                    / VOLTS_TO_COUNTS_FACTOR,
                )

            return history, slow_values
        return [], []

    def enable_area_selection(self, selectable_width=0.5):
        self.selection_running = True

        # there are some glitches if the width of the overlay is exactly right.
        # Therefore we make it a little wider.
        extra_width = N_POINTS / 100
        boundary_width = (N_POINTS * (1 - selectable_width)) / 2.0

        self.selection_boundaries = (boundary_width, N_POINTS - boundary_width)

        self.boundary_overlays[0].setRegion((-extra_width, boundary_width))
        self.boundary_overlays[1].setRegion(
            (N_POINTS - boundary_width, N_POINTS + extra_width)
        )

        for overlay in self.boundary_overlays:
            overlay.setVisible(True)

    def disable_area_selection(self):
        self.selection_running = False

        for overlay in self.boundary_overlays:
            overlay.setVisible(False)

    def pause_plot(self) -> None:
        """
        Pauses plot updates. All incoming data is cached though. This is useful for
        letting the user select a line that is then used in the autolock.
        """
        self.plot_paused = True

    def resume_plot_and_clear_cache(self):
        """Resume plotting again."""
        self.plot_paused = False
        self.cached_plot_data = []

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

    def show_control_thresholds(self, show: bool, min_: float, max_: float) -> None:
        if self.app.parameters.lock.value:
            self.control_signal_threshold_min.setAngle(0)
            self.control_signal_threshold_max.setAngle(0)
        else:
            sweep_center = self.app.parameters.sweep_center.value
            sweep_amplitude = self.app.parameters.sweep_amplitude.value
            sweep_min = sweep_center - sweep_amplitude
            sweep_max = sweep_center + sweep_amplitude
            spacing = (N_POINTS - 1) / abs(sweep_max - sweep_min)  # pts / V
            min_ = spacing * (min_ - sweep_min)
            max_ = spacing * (max_ - sweep_min)
            self.control_signal_threshold_min.setAngle(90)
            self.control_signal_threshold_max.setAngle(90)
        self.control_signal_threshold_min.setValue(min_)
        self.control_signal_threshold_max.setValue(max_)
        self.control_signal_threshold_min.setVisible(show)
        self.control_signal_threshold_max.setVisible(show)

    def show_error_thresholds(self, show: bool, min_: float, max_: float) -> None:
        self.error_signal_threshold_min.setValue(min_)
        self.error_signal_threshold_max.setValue(max_)
        self.error_signal_threshold_min.setVisible(show)
        self.error_signal_threshold_max.setVisible(show)

    def show_monitor_thresholds(self, show: bool, min_: float, max_: float) -> None:
        self.monitor_signal_threshold_min.setValue(min_)
        self.monitor_signal_threshold_max.setValue(max_)
        self.monitor_signal_threshold_min.setVisible(show)
        self.monitor_signal_threshold_max.setVisible(show)


def scale_history_times(arr: np.ndarray, timescale: int) -> np.ndarray:
    if arr:
        arr = np.array(arr)
        arr -= arr[0]
        arr *= 1 / timescale * N_POINTS
    return arr
