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

import numpy as np
import pyqtgraph as pg
from linien_gui.ui.plot_widget import V
from linien_gui.utils import get_linien_app_instance


class CustomLogAxis(pg.AxisItem):
    """This class overrides the tick label generator function of the default
    axis. It reimplements it such that negative exponents are also displayed
    in scientific notation."""

    def __init__(self, *args, **kwargs):
        pg.AxisItem.__init__(self, *args, **kwargs)

    def logTickStrings(self, values, scale, spacing):
        # this method is mainly taken from pyqtgraph, just taking care that negative
        # exponents are also displayed in scientific notation
        estrings = [
            "%0.1e" % x for x in 10 ** np.array(values).astype(float) * np.array(scale)
        ]

        convdict = {
            "0": "⁰",
            "1": "¹",
            "2": "²",
            "3": "³",
            "4": "⁴",
            "5": "⁵",
            "6": "⁶",
            "7": "⁷",
            "8": "⁸",
            "9": "⁹",
        }
        dstrings = []
        for e in estrings:
            if e.count("e"):
                v, p = e.split("e")

                sign = "⁻" if p[0] == "-" else ""
                if p[1:].count("0") == len(p[1:]):
                    pot = convdict["0"]
                else:
                    pot = "".join([convdict[pp] for pp in p[1:].lstrip("0")])

                v = v.rstrip(".0")

                if v == "1":
                    v = ""
                else:
                    v = v + "·"
                dstrings.append(v + "10" + sign + pot)
            else:
                dstrings.append(e)

        return dstrings


class PSDPlotWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super(PSDPlotWidget, self).__init__(
            *args,
            axisItems={
                "bottom": CustomLogAxis(orientation="bottom"),
                "left": CustomLogAxis(orientation="left"),
            },
            **kwargs
        )
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.curves = {}

        self.setLogMode(x=True, y=True)
        self.setLabel("left", "PSD", units="V / Sqrt[Hz]")
        self.setLabel("bottom", "Frequency", units="Hz")
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("bottom").enableAutoSIPrefix(False)
        self.showGrid(x=True, y=True)

        self.vertical_line = pg.InfiniteLine(angle=90, movable=False)
        self.vertical_line.hide()
        self.horizontal_line = pg.InfiniteLine(angle=0, movable=False)
        self.horizontal_line.hide()
        self.cursor_label = pg.TextItem()
        self.scene().sigMouseMoved.connect(self.mouseMoved)

        for element in (self.vertical_line, self.horizontal_line, self.cursor_label):
            # ignoreBounds tells pyqtgraph not to consider these items when calculating
            # automatic axis scaling
            self.addItem(element, ignoreBounds=True)
            # all these elements should be on top of all plots
            element.setZValue(10000)

        self.recalculate_min_max()

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

    def plot_curve(self, uuid, psds, color):
        self.curves[uuid] = self.curves.get(uuid, [])
        for idx in range(len(psds)):
            if len(self.curves[uuid]) <= idx:
                curve = pg.PlotCurveItem()
                self.curves[uuid].append(curve)
                self.addItem(curve)

        # sort such that high decimations are first
        psds_sorted = sorted(psds.items(), key=lambda v: -1 * v[0])
        highest_plotted_frequency = 0
        highest_plotted_frequency_psd = None

        for idx, [decimation, [f, psd]] in enumerate(psds_sorted):
            curve = self.curves[uuid][idx]

            psd = psd[f > highest_plotted_frequency]
            f = f[f > highest_plotted_frequency]

            if highest_plotted_frequency_psd is not None:
                # this connects first and last points of adjacent segments
                f = np.array([highest_plotted_frequency] + list(f))
                psd = np.array([highest_plotted_frequency_psd] + list(psd))

            highest_plotted_frequency = f[-1]
            highest_plotted_frequency_psd = psd[-1]

            curve.setData(np.log10(f), np.log10(psd / V))
            r, g, b = color
            curve.setPen(pg.mkPen((r, g, b, 200)))

        self.recalculate_min_max()

    def recalculate_min_max(self):
        self._x_min = np.inf
        self._x_max = -np.inf
        self._y_min = np.inf
        self._y_max = -np.inf

        if self.curves:
            for curves in self.curves.values():
                for curve in curves:
                    x, y = curve.getData()
                    if np.min(x) < self._x_min:
                        self._x_min = np.min(x)
                    if np.max(x) > self._x_max:
                        self._x_max = np.max(x)
                    if np.min(y) < self._y_min:
                        self._y_min = np.min(y)
                    if np.max(y) > self._y_max:
                        self._y_max = np.max(y)

    def show_or_hide_curve(self, uuid, show):
        curves = self.curves.get(uuid, [])

        for curve in curves:
            curve.setVisible(show)

    def delete_curve(self, uuid):
        for curve in self.curves[uuid]:
            self.removeItem(curve)
        del self.curves[uuid]

    def _to_data_coords(self, event):
        pos = self.plotItem.vb.mapSceneToView(event.pos())
        x, y = pos.x(), pos.y()
        return x, y

    def mouseMoved(self, evt):
        pos = evt

        if self.sceneBoundingRect().contains(pos):
            mousePoint = self.plotItem.vb.mapSceneToView(pos)
            x = mousePoint.x()
            y = mousePoint.y()

            # if index > 0 and index < self.MFmax:
            self.cursor_label.setHtml(
                "<span style='font-size: 12pt'>(%.1e,%.1e)</span>" % (10**x, 10**y)
            )
            # this determines whether cursor label is on right or left side of
            # crosshair
            self.cursor_label.setAnchor((1 if x > self._x_max / 2 else 0, 1))
            self.cursor_label.setPos(x, y)
            self.vertical_line.setPos(x)
            self.horizontal_line.setPos(y)

            self.show_cursor_position(True)
        else:
            self.show_cursor_position(False)

    def show_cursor_position(self, show):
        self.vertical_line.setVisible(show)
        self.horizontal_line.setVisible(show)
        self.cursor_label.setVisible(show)

    def leaveEvent(self, QEvent):
        """This method is called when the mouse used to hover the plot and
        not left. In this case, we hide crosshair and cursor label."""
        super().leaveEvent(QEvent)
        self.show_cursor_position(False)
