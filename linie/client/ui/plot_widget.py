import math
import pickle
import numpy as np
from PyQt5 import QtGui, QtWidgets
from linie.client.widgets import CustomWidget
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from time import time
from linie.common import update_control_signal_history


class PlotWidget(pg.PlotWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hideAxis('bottom')
        self.hideAxis('left')

        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        # important: increasing pen width makes plotting much slower!
        # alternative: pg.setConfigOptions(useOpenGL=True)
        # see: https://github.com/pyqtgraph/pyqtgraph/issues/533
        pen_width = 1

        self.zero_line = pg.PlotCurveItem(pen=pg.mkPen('w', width=1))
        self.addItem(self.zero_line)
        self.signal = pg.PlotCurveItem(pen=pg.mkPen((200, 0, 0, 200), width=pen_width))
        self.addItem(self.signal)
        self.control_signal = pg.PlotCurveItem(pen=pg.mkPen((0, 0, 200, 200), width=pen_width))
        self.addItem(self.control_signal)
        self.control_signal_history = pg.PlotCurveItem(pen=pg.mkPen((0, 200, 0, 200), width=pen_width))
        self.addItem(self.control_signal_history)

        self.zero_line.setData([0, 16383], [0, 0])
        self.signal.setData([0, 16383], [1, 1])

        self.connection = None
        self.parameters = None
        self.last_plot_rescale = 0
        self.last_plot_data = None
        self.plot_max = 0
        self.plot_min = np.inf
        self.touch_start = None

        self.init_overlay()

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
                self.control.start_autolock(
                    *sorted([x0, x]),
                    self.last_plot_data[0]
                )
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
        print('on_click', x,y)
        center = x / self.xmax
        center = (center - 0.5) * 2
        center = self.parameters.center.value + \
            (center * self.parameters.ramp_amplitude.value)

        self.parameters.ramp_amplitude.value /= 2
        self.parameters.center.value = center
        self.control.write_data()

    def replot(self, to_plot):
        if to_plot is not None and not self.touch_start:
            to_plot = pickle.loads(to_plot)

            if to_plot is None:
                return

            self.last_plot_data = to_plot

            error_signal, control_signal = to_plot

            self.signal.setData(list(range(len(error_signal))), error_signal)
            self.control_signal.setData(
                list(range(len(error_signal))),
                [
                    point / 8192 * self.plot_max
                    for point in control_signal
                ]
            )

            self.plot_max = np.max([-1 * self.plot_min, self.plot_max, math.ceil(np.max(error_signal))])
            self.plot_min = np.min([-1 * self.plot_max, self.plot_min, math.floor(np.min(error_signal))])

            if time() - self.last_plot_rescale > 2:
                plot_min = math.floor(self.plot_min)
                plot_max = math.ceil(self.plot_max)

                if plot_min == plot_max:
                    plot_max += 1

                self.setYRange(plot_min, plot_max)

                self.last_plot_rescale = time()

            self.control_history_data = update_control_signal_history(
                self.control_signal_history_data,
                to_plot,
                # FIXME: this causes an unnecessary call every time!
                self.control.exposed_is_locked
            )
            # FIXME: this causes an unnecessary call every time!
            if self.control.exposed_is_locked:
                self.control_signal_history.setData(
                    # FIXME: Scale x axis correctly
                    list(range(len(self.control_signal_history_data))),
                    [
                        point / 8192 * self.plot_max
                        for point in self.control_signal_history_data
                    ]
                )
