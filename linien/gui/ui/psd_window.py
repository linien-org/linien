import pickle
import random
import string
import numpy as np

import pyqtgraph as pg
from linien.gui.utils_gui import hex_to_color, set_window_icon
from linien.gui.widgets import CustomWidget
from PyQt5 import QtGui


class RandomColorChoser:
    def __init__(self):
        self.index = 0
        # pick one to turn into an actual colormap
        # generated using https://mokole.com/palette.html
        # and shuffled using random.shuffle
        self.lut = [
            "#2e8b57",
            "#0000ff",
            "#87cefa",
            "#ff1493",
            "#adff2f",
            "#b03060",
            "#6495ed",
            "#90ee90",
            "#dc143c",
            "#ffff00",
            "#483d8b",
            "#f08080",
            "#8b4513",
            "#00ff00",
            "#da70d6",
            "#f4a460",
            "#008000",
            "#00ff7f",
            "#808000",
            "#7b68ee",
            "#a9a9a9",
            "#ff8c00",
            "#00008b",
            "#f0e68c",
            "#ff0000",
            "#800080",
            "#2f4f4f",
            "#ff00ff",
            "#00ffff",
            "#8a2be2",
        ]

    def get(self):
        color = self.lut[self.index]
        if self.index < len(self.lut) - 1:
            self.index += 1
        else:
            self.index = 0

        return hex_to_color(color)


class PSDWindow(QtGui.QMainWindow, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("psd_window.ui")
        self.setWindowTitle("Linien: Noise analysis")
        set_window_icon(self)
        self.random_color_choser = RandomColorChoser()

    def ready(self):
        self.ids.start_psd_button.clicked.connect(self.start_psd)
        self.ids.curve_table.show_or_hide_curve.connect(
            self.ids.psd_plot_widget.show_or_hide_curve
        )
        self.ids.delete_curve_button.clicked.connect(self.delete_curve)

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

        curve_uuid = "".join(random.choice(string.ascii_lowercase) for i in range(10))
        color = self.random_color_choser.get()
        self.ids.psd_plot_widget.plot_curve(curve_uuid, data["psds"], color)
        self.ids.curve_table.add_curve(curve_uuid, data, color)

    def start_psd(self):
        self.control.start_pid_optimization()

    def delete_curve(self):
        uuid = self.ids.curve_table.delete_selected_curve()
        self.ids.psd_plot_widget.delete_curve(uuid)