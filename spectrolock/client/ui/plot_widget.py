import math
import numpy as np
from PyQt5 import QtGui, QtWidgets
from spectrolock.client.widgets import CustomWidget
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from time import time


class PlotWidget(pg.PlotWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)

        self.signal = pg.PlotCurveItem(pen=pg.mkPen('g', width=3))
        self.addItem(self.signal)
        self.control_signal = pg.PlotCurveItem(pen=pg.mkPen('r', width=3))
        self.addItem(self.control_signal)
        self.zero_line = pg.PlotCurveItem(pen=pg.mkPen('w', width=1))
        self.addItem(self.zero_line)

        self.zero_line.setData([-1, 10000], [0, 0])
        self.signal.setData([-1, 10000], [1, 1])

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

    def mouseClickevent(self, event):
        print('CLICK', event)

    def mouseMoveEvent(self, event):
        if self.touch_start is None:
            return

        x0, y0 = self.touch_start

        x, y = self._to_data_coords(event)
        self.set_selection_overlay(x0, x - x0)

    def init_overlay(self):
        self.overlay = pg.QtGui.QGraphicsRectItem(0, 0, 0, 0)
        self.overlay.setPen(pg.mkPen(None))
        self.overlay.setBrush(pg.mkBrush('r'))
        vb = self.plotItem.vb
        vb.addItem(self.overlay)

    def set_selection_overlay(self, x_start, width):
        self.overlay.setRect(x_start, 0, width, 10000)

    def mousePressEvent(self, event):
        x, y = self._to_data_coords(event)

        self.touch_start = x, y

    def mouseReleaseEvent(self, event):
        pg.PlotWidget.mouseReleaseEvent(self, event)

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
                    start_watching=self.ids.watch_lock_checkbox.active
                )
            else:
                self.graph_on_selection(x0, x)

        self.set_selection_overlay(0, 0)
        self.touch_start = None

    def connection_established(self, app):
        self.app = app
        self.control = app.control
        self.parameters = self.app.parameters

        self.parameters.to_plot.change(self.replot)

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
        if to_plot is not None:
            self.last_plot_data = to_plot

            error_signal, control_signal = to_plot

            self.parameters.to_plot.value = None
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
                self.setYRange(math.floor(self.plot_min), math.ceil(self.plot_max))
                # FIXME:missing
                #self.ids.graph.xmax = len(error_signal)
                #self.ids.graph.y_ticks_major = int(self.plot_max * 2 / 5)

                #if self.ids.graph.ymin == self.ids.graph.ymax:
                #    self.ids.graph.ymax += 1

                self.last_plot_rescale = time()