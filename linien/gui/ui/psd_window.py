import linien
import pickle
import json
import numpy as np

from time import time
from linien.gui.utils_gui import RandomColorChoser, set_window_icon
from linien.gui.widgets import CustomWidget
from PyQt5 import QtGui, QtWidgets


class PSDWindow(QtGui.QMainWindow, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("psd_window.ui")
        self.setWindowTitle("Linien: Noise analysis")
        set_window_icon(self)
        self.random_color_choser = RandomColorChoser()
        self.colors = {}
        self.data = {}

    def ready(self):
        self.ids.start_psd_button.clicked.connect(self.start_psd)
        self.ids.start_pid_optimization_button.clicked.connect(
            self.start_pid_optimization
        )

        self.ids.curve_table.show_or_hide_curve.connect(
            self.ids.psd_plot_widget.show_or_hide_curve
        )
        self.ids.delete_curve_button.clicked.connect(self.delete_curve)
        self.ids.export_psd_button.clicked.connect(self.export_psd)
        self.ids.import_psd_button.clicked.connect(self.import_psd)

    def connection_established(self):
        self.control = self.app.control
        params = self.app.parameters
        self.parameters = params

        self.parameters.psd_data.on_change(
            self.psd_data_received,
        )

    def psd_data_received(self, data_pickled):
        if data_pickled is None:
            return

        data = pickle.loads(data_pickled)

        curve_uuid = data["uuid"]
        if curve_uuid not in self.colors:
            color = self.random_color_choser.get()
            self.colors[curve_uuid] = color
        else:
            color = self.colors[curve_uuid]

        self.ids.psd_plot_widget.plot_curve(curve_uuid, data["psds"], color)
        self.ids.curve_table.add_curve(curve_uuid, data, color)

        self.data[curve_uuid] = data

    def start_psd(self):
        self.control.start_psd_acquisition()

    def start_pid_optimization(self):
        self.control.start_pid_optimization()

    def delete_curve(self):
        uuid = self.ids.curve_table.delete_selected_curve()
        self.ids.psd_plot_widget.delete_curve(uuid)
        del self.data[uuid]

    def export_psd(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".json"
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            "JSON (*%s)" % default_ext,
            options=options,
        )
        if fn:
            if not fn.endswith(default_ext):
                fn = fn + default_ext

            with open(fn, "w") as f:
                json.dump(
                    {
                        "linien-version": linien.__version__,
                        "time": time(),
                        "psd-data": self.data,
                    },
                    f,
                )

    def import_psd(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".json"
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            "JSON (*%s)" % default_ext,
            options=options,
        )
        if fn:
            with open(fn, "r") as f:
                data = json.load(f)

            assert "linien-version" in data, "invalid parameter file"

            for uuid, psd_data in data["psd-data"].items():
                self.psd_data_received(pickle.dumps(psd_data))