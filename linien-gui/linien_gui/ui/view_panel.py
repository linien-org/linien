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

import json
import pickle
from os import path

import numpy as np
from linien_gui.config import N_COLORS, UI_PATH
from linien_gui.ui.spin_box import CustomDoubleSpinBoxNoSign, CustomSpinBox
from linien_gui.utils import color_to_hex, get_linien_app_instance, param2ui
from PyQt5 import QtGui, QtWidgets, uic


class ViewPanel(QtWidgets.QWidget):
    plotLineWidthSpinBox: CustomDoubleSpinBoxNoSign
    plotLineOpacitySpinBox: CustomSpinBox
    plotFillOpacitySpinBox: CustomSpinBox
    displayColorLabel0: QtWidgets.QLabel
    displayColorLabel1: QtWidgets.QLabel
    displayColorLabel2: QtWidgets.QLabel
    displayColorLabel3: QtWidgets.QLabel
    displayColorLabel4: QtWidgets.QLabel
    editColorButton0: QtWidgets.QToolButton
    editColorButton1: QtWidgets.QToolButton
    editColorButton2: QtWidgets.QToolButton
    editColorButton3: QtWidgets.QToolButton
    editColorButton4: QtWidgets.QToolButton
    exportDataPushButton: QtWidgets.QPushButton
    exportSelectFilePushButton: QtWidgets.QPushButton

    def __init__(self, *args, **kwargs):
        super(ViewPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "view_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.exportSelectFilePushButton.clicked.connect(self.export_select_file)
        self.exportDataPushButton.clicked.connect(self.export_data)

        self.plotLineWidthSpinBox.setKeyboardTracking(False)
        self.plotLineWidthSpinBox.valueChanged.connect(self.on_plot_line_width_changed)

        self.plotLineOpacitySpinBox.setKeyboardTracking(False)
        self.plotLineOpacitySpinBox.valueChanged.connect(
            self.on_plot_line_opacity_changed
        )

        self.plotFillOpacitySpinBox.setKeyboardTracking(False)
        self.plotFillOpacitySpinBox.valueChanged.connect(
            self.on_plot_fill_opacity_changed
        )

        for color_idx in range(N_COLORS):
            getattr(self, f"editColorButton{color_idx}").clicked.connect(
                lambda *args, color_idx=color_idx: self.edit_color(color_idx)
            )

    def edit_color(self, color_idx):
        setting = getattr(self.app.settings, f"plot_color_{color_idx}")
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor.fromRgb(*setting.value))
        r, g, b, a = color.getRgb()
        getattr(self.app.settings, f"plot_color_{color_idx}").value = (r, g, b, a)

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.app.settings.plot_line_width, self.plotLineWidthSpinBox)
        param2ui(self.app.settings.plot_line_opacity, self.plotLineOpacitySpinBox)
        param2ui(self.app.settings.plot_fill_opacity, self.plotFillOpacitySpinBox)

        def preview_colors(*args):
            for color_idx in range(N_COLORS):
                element = getattr(self, f"displayColorLabel{color_idx}")
                setting = getattr(self.app.settings, f"plot_color_{color_idx}")
                element.setStyleSheet(
                    f"background-color: {color_to_hex(setting.value)}"
                )

        for color_idx in range(N_COLORS):
            getattr(self.app.settings, f"plot_color_{color_idx}").add_callback(
                preview_colors
            )

    def on_plot_line_width_changed(self):
        self.app.settings.plot_line_width.value = self.plotLineWidthSpinBox.value()

    def on_plot_line_opacity_changed(self):
        self.app.settings.plot_line_opacity.value = self.plotLineOpacitySpinBox.value()

    def on_plot_fill_opacity_changed(self):
        self.app.settings.plot_fill_opacity.value = self.plotFillOpacitySpinBox.value()

    def export_select_file(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".json"
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            f"JSON (*{default_ext})",
            options=options,
        )
        if fn:
            if not fn.endswith(default_ext):
                fn = fn + default_ext
            self.export_fn = fn
            self.exportSelectFilePushButton.setText(
                f"File selected: {path.split(fn)[-1]}"
            )
            self.exportDataPushButton.setEnabled(True)

    def export_data(self):
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

        print(f"export data to {fn_with_suffix}")

        with open(fn_with_suffix, "w") as f:
            data = pickle.loads(self.parameters.to_plot.value)

            # filter out keys that are not json-able
            for k, v in list(data.items()):
                if isinstance(v, np.ndarray):
                    data[k] = v.tolist()

            json.dump(data, f)
