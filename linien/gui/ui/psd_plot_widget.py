from linien.gui.ui.plot_widget import V
import numpy as np
import pyqtgraph as pg
from linien.gui.widgets import CustomWidget


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


class PSDPlotWidget(pg.PlotWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            axisItems={
                "bottom": CustomLogAxis(orientation="bottom"),
                "left": CustomLogAxis(orientation="left"),
            },
            **kwargs
        )

        self.curves = {}

        self.setLogMode(x=True, y=True)
        self.setLabel("left", "PSD", units="V / Sqrt[Hz]")
        self.setLabel("bottom", "Frequency", units="Hz")
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("bottom").enableAutoSIPrefix(False)
        self.showGrid(x=True, y=True)

    def connection_established(self):
        self.control = self.app().control
        self.parameters = self.app().parameters

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
        for idx, [decimation, [f, psd]] in enumerate(psds_sorted):
            curve = self.curves[uuid][idx]

            psd = psd[f > highest_plotted_frequency]
            f = f[f > highest_plotted_frequency]
            highest_plotted_frequency = f[-1]

            curve.setData(np.log10(f), np.log10(psd / V))
            r, g, b = color
            curve.setPen(pg.mkPen((r, g, b, 200)))

    def show_or_hide_curve(self, uuid, show):
        curves = self.curves.get(uuid, [])

        for curve in curves:
            curve.setVisible(show)

    def delete_curve(self, uuid):
        for curve in self.curves[uuid]:
            self.removeItem(curve)
        del self.curves[uuid]