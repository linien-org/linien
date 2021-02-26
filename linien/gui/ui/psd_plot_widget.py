import numpy as np
import pyqtgraph as pg
from linien.gui.widgets import CustomWidget


class PSDPlotWidget(pg.PlotWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._fixed_opengl_bug = False

        self.curves = {}

        self.setLogMode(x=True, y=True)
        self.setLabel("left", "PSD", units="X")
        self.setLabel("bottom", "Frequency", units="Hz")
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("bottom").enableAutoSIPrefix(False)
        self.showGrid(x=True, y=True)

    def connection_established(self):
        self.control = self.app().control
        self.parameters = self.app().parameters

        if not self._fixed_opengl_bug:
            self._fixed_opengl_bug = True
            self.resize(
                self.parent().frameGeometry().width(),
                self.parent().frameGeometry().height(),
            )

    def plot_curve(self, uuid, psds, color):
        self.curves[uuid] = []

        for decimation, [f, psd] in psds.items():
            curve = pg.PlotCurveItem()
            self.addItem(curve)
            curve.setData(np.log10(f), np.log10(psd))
            r, g, b = color
            curve.setPen(pg.mkPen((r, g, b, 200)))
            self.curves[uuid].append(curve)

    def show_or_hide_curve(self, uuid, show):
        curves = self.curves.get(uuid, [])

        for curve in curves:
            curve.setVisible(show)

    def delete_curve(self, uuid):
        for curve in self.curves[uuid]:
            self.removeItem(curve)
        del self.curves[uuid]