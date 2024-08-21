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
import logging
import pickle
from os import path

import numpy as np
from linien_gui.config import UI_PATH, Setting
from linien_gui.ui.spin_box import CustomDoubleSpinBoxNoSign, CustomSpinBox
from linien_gui.utils import color_to_hex, get_linien_app_instance, param2ui
from PyQt5 import QtGui, QtWidgets, uic

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ViewPanel(QtWidgets.QWidget):
    plotLineWidthSpinBox: CustomDoubleSpinBoxNoSign
    plotLineOpacitySpinBox: CustomSpinBox
    plotFillOpacitySpinBox: CustomSpinBox
    colorPreviewLabelErrorCombined: QtWidgets.QLabel
    colorPreviewLabelError1: QtWidgets.QLabel
    colorPreviewLabelError2: QtWidgets.QLabel
    colorPreviewLabelMonitor: QtWidgets.QLabel
    colorPreviewLabelMonitorHistory: QtWidgets.QLabel
    colorPreviewLabelControl: QtWidgets.QLabel
    colorPreviewLabelControlHistory: QtWidgets.QLabel
    colorPreviewLabelSlowControl: QtWidgets.QLabel
    editColorButtonErrorCombined: QtWidgets.QToolButton
    editColorButtonError1: QtWidgets.QToolButton
    editColorButtonError2: QtWidgets.QToolButton
    editColorButtonMonitor: QtWidgets.QToolButton
    editColorButtonMonitorHistory: QtWidgets.QToolButton
    editColorButtonControl: QtWidgets.QToolButton
    editColorButtonControlHistory: QtWidgets.QToolButton
    editColorButtonSlowControl: QtWidgets.QToolButton
    exportDataPushButton: QtWidgets.QPushButton
    exportSelectFilePushButton: QtWidgets.QPushButton

    def __init__(self, *args, **kwargs):
        super(ViewPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "view_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.exportSelectFilePushButton.clicked.connect(self.on_export_button_clicked)
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

        # connect color edit buttons to settings
        for button, setting in {
            self.editColorButtonErrorCombined: self.app.settings.plot_color_error_combined,  # noqa : E501
            self.editColorButtonError1: self.app.settings.plot_color_error1,
            self.editColorButtonError2: self.app.settings.plot_color_error2,
            self.editColorButtonMonitor: self.app.settings.plot_color_monitor,
            self.editColorButtonMonitorHistory: self.app.settings.plot_color_monitor_history,  # noqa: E501
            self.editColorButtonControl: self.app.settings.plot_color_control,
            self.editColorButtonControlHistory: self.app.settings.plot_color_control_history,  # noqa: E501
            self.editColorButtonSlowControl: self.app.settings.plot_color_slow_control,
        }.items():
            button.clicked.connect(
                lambda *_, setting=setting: self.on_edit_color_clicked(setting=setting)
            )

        # connect preview labels to settings by creating callback functions for each
        # label : color-settings pair
        for preview_label, setting in {
            self.colorPreviewLabelErrorCombined: self.app.settings.plot_color_error_combined,  # noqa : E501
            self.colorPreviewLabelError1: self.app.settings.plot_color_error1,
            self.colorPreviewLabelError2: self.app.settings.plot_color_error2,
            self.colorPreviewLabelMonitor: self.app.settings.plot_color_monitor,
            self.colorPreviewLabelMonitorHistory: self.app.settings.plot_color_monitor_history,  # noqa: E501
            self.colorPreviewLabelControl: self.app.settings.plot_color_control,
            self.colorPreviewLabelControlHistory: self.app.settings.plot_color_control_history,  # noqa: E501
            self.colorPreviewLabelSlowControl: self.app.settings.plot_color_slow_control,  # noqa: E501
        }.items():
            setting.add_callback(
                lambda val, label=preview_label: label.setStyleSheet(
                    f"background-color: {color_to_hex(val)}"
                )
            )

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.app.settings.plot_line_width, self.plotLineWidthSpinBox)
        param2ui(self.app.settings.plot_line_opacity, self.plotLineOpacitySpinBox)
        param2ui(self.app.settings.plot_fill_opacity, self.plotFillOpacitySpinBox)

    def on_edit_color_clicked(self, setting: Setting) -> None:
        """Choose new color via a color selection window and write it to setting"""
        old_color = setting.value
        new_color = QtWidgets.QColorDialog.getColor(QtGui.QColor.fromRgb(*old_color))
        r, g, b, _ = new_color.getRgb()
        setting.value = (r, g, b)

    def on_plot_line_width_changed(self):
        self.app.settings.plot_line_width.value = self.plotLineWidthSpinBox.value()

    def on_plot_line_opacity_changed(self):
        self.app.settings.plot_line_opacity.value = self.plotLineOpacitySpinBox.value()

    def on_plot_fill_opacity_changed(self):
        self.app.settings.plot_fill_opacity.value = self.plotFillOpacitySpinBox.value()

    def on_export_button_clicked(self):
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

        logger.info(f"Exported view data to {fn_with_suffix}")

        with open(fn_with_suffix, "w") as f:
            data = pickle.loads(self.parameters.to_plot.value)

            # filter out keys that are not json-able
            for k, v in list(data.items()):
                if isinstance(v, np.ndarray):
                    data[k] = v.tolist()

            json.dump(data, f)
