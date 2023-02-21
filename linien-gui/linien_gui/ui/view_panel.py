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

import json
import pickle
from os import path

import numpy as np
from linien_common.config import N_COLORS
from linien_gui.utils_gui import color_to_hex, param2ui
from linien_gui.widgets import CustomWidget
from PyQt5 import QtGui, QtWidgets


class ViewPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("view_panel.ui")

    def ready(self):
        self.ids.export_select_file.clicked.connect(self.do_export_select_file)
        self.ids.export_data.clicked.connect(self.do_export_data)

        self.ids.plot_line_width.setKeyboardTracking(False)
        self.ids.plot_line_width.valueChanged.connect(self.plot_line_width_changed)

        self.ids.plot_line_opacity.setKeyboardTracking(False)
        self.ids.plot_line_opacity.valueChanged.connect(self.plot_line_opacity_changed)

        self.ids.plot_fill_opacity.setKeyboardTracking(False)
        self.ids.plot_fill_opacity.valueChanged.connect(self.plot_fill_opacity_changed)

        for color_idx in range(N_COLORS):
            getattr(self.ids, "edit_color_%d" % color_idx).clicked.connect(
                lambda *args, color_idx=color_idx: self.edit_color(color_idx)
            )

    def edit_color(self, color_idx):
        param = getattr(self.parameters, "plot_color_%d" % color_idx)

        color = QtWidgets.QColorDialog.getColor(QtGui.QColor.fromRgb(*param.value))
        r, g, b, a = color.getRgb()
        print("set color", color_idx, color.getRgb())
        param.value = (r, g, b, a)

    def connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.parameters.plot_line_width, self.ids.plot_line_width)
        param2ui(self.parameters.plot_line_opacity, self.ids.plot_line_opacity)
        param2ui(self.parameters.plot_fill_opacity, self.ids.plot_fill_opacity)

        def preview_colors(*args):
            for color_idx in range(N_COLORS):
                element = getattr(self.ids, "display_color_%d" % color_idx)
                param = getattr(self.parameters, "plot_color_%d" % color_idx)
                element.setStyleSheet("background-color: " + color_to_hex(param.value))

        for color_idx in range(N_COLORS):
            getattr(self.parameters, "plot_color_%d" % color_idx).on_change(
                preview_colors
            )

    def plot_line_width_changed(self):
        self.parameters.plot_line_width.value = self.ids.plot_line_width.value()

    def plot_line_opacity_changed(self):
        self.parameters.plot_line_opacity.value = self.ids.plot_line_opacity.value()

    def plot_fill_opacity_changed(self):
        self.parameters.plot_fill_opacity.value = self.ids.plot_fill_opacity.value()

    def do_export_select_file(self):
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
            self.export_fn = fn
            self.ids.export_select_file.setText(
                "File selected: %s" % path.split(fn)[-1]
            )
            self.ids.export_data.setEnabled(True)

    def do_export_data(self):
        fn = self.export_fn
        counter = 0

        while True:
            if counter > 0:
                name, ext = path.splitext(fn)
                fn_with_suffix = name + "-" + str(counter)
                if ext:
                    fn_with_suffix += ext
            else:
                fn_with_suffix = fn

            try:
                open(fn_with_suffix, "r")
                counter += 1
                continue
            except FileNotFoundError:
                break

        print("export data to", fn_with_suffix)

        with open(fn_with_suffix, "w") as f:
            data = pickle.loads(self.parameters.to_plot.value)

            # filter out keys that are not json-able
            for k, v in list(data.items()):
                if isinstance(v, np.ndarray):
                    data[k] = v.tolist()

            json.dump(data, f)
