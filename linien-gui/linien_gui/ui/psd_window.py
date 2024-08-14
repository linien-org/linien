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

import pickle
from time import time

import linien_gui
from linien_common.common import PSDAlgorithm
from linien_gui.config import UI_PATH
from linien_gui.dialogs import error_dialog
from linien_gui.ui.psd_plot_widget import PSDPlotWidget
from linien_gui.ui.psd_table_widget import PSDTableWidget
from linien_gui.utils import (
    RandomColorChoser,
    get_linien_app_instance,
    param2ui,
    set_window_icon,
)
from PyQt5 import QtWidgets, uic


class PSDWindow(QtWidgets.QMainWindow):
    PSDPlot: PSDPlotWidget
    curveTable: PSDTableWidget
    maxMeasurementTimeComboBox: QtWidgets.QComboBox
    PSDAlgorithmComboBox: QtWidgets.QComboBox
    startPSDPushButton: QtWidgets.QPushButton
    stopPSDPushButton: QtWidgets.QPushButton
    exportPSDPushButton: QtWidgets.QPushButton
    importPSDPushButton: QtWidgets.QPushButton
    deleteCurveButton: QtWidgets.QPushButton
    PSDRunningContainer: QtWidgets.QWidget
    PSDNotRunningContainer: QtWidgets.QGroupBox

    def __init__(self, *args, **kwargs):
        super(PSDWindow, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "psd_window.ui", self)
        self.setWindowTitle("Linien: Noise analysis")
        set_window_icon(self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.random_color_choser = RandomColorChoser()
        self.colors = {}
        self.data = {}
        self.complete_uids = []

        self.startPSDPushButton.clicked.connect(self.start_psd)
        self.stopPSDPushButton.clicked.connect(self.stop_psd)

        self.curveTable.show_or_hide_curve.connect(self.PSDPlot.show_or_hide_curve)
        self.deleteCurveButton.clicked.connect(self.delete_curve)
        self.exportPSDPushButton.clicked.connect(self.export_psd)
        self.importPSDPushButton.clicked.connect(self.import_psd)

        self.maxMeasurementTimeComboBox.currentIndexChanged.connect(
            self.on_maximum_measurement_time_changed
        )

        self.PSDAlgorithmComboBox.currentIndexChanged.connect(self.change_psd_algorithm)

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        self.parameters.psd_data_partial.add_callback(
            self.psd_data_received,
        )
        self.parameters.psd_data_complete.add_callback(
            self.psd_data_received,
        )

        param2ui(
            self.parameters.psd_acquisition_max_decimation,
            self.maxMeasurementTimeComboBox,
            lambda max_decimation: max_decimation - 12,
        )
        param2ui(self.parameters.psd_algorithm, self.PSDAlgorithmComboBox)

        def update_status(_):
            psd_running = self.parameters.psd_acquisition_running.value
            if psd_running:
                self.PSDRunningContainer.show()
                self.PSDNotRunningContainer.hide()
            else:
                self.PSDRunningContainer.hide()
                self.PSDNotRunningContainer.show()

        self.parameters.psd_acquisition_running.add_callback(update_status)

    def closeEvent(self, event, *args, **kwargs):
        # we never really want to close the window (which destroys its content)  but
        # just to hide it
        event.ignore()
        self.hide()

    def on_maximum_measurement_time_changed(self, index):
        self.parameters.psd_acquisition_max_decimation.value = 12 + index

    def change_psd_algorithm(self, index: int) -> None:
        self.parameters.psd_algorithm.value = list(PSDAlgorithm)[index]

    def psd_data_received(self, data_pickled):
        if data_pickled is None:
            return

        data = pickle.loads(data_pickled)

        curve_uuid = data["uuid"]

        if curve_uuid in self.complete_uids:
            # in networks with high latency it may happen that psd data is not received
            # in order. We do not want to update a complete plot with a partial one
            # --> stop here
            return

        if data["complete"]:
            self.complete_uids.append(curve_uuid)

        # either reuse the color of the previous partial plot of this curve or generate
        # a new color if the curve was not yet partially plotted
        if curve_uuid not in self.colors:
            color = self.random_color_choser.get()
            self.colors[curve_uuid] = color
        else:
            color = self.colors[curve_uuid]

        self.PSDPlot.plot_curve(curve_uuid, data["psds"], color)
        self.curveTable.add_curve(curve_uuid, data, color)

        self.data[curve_uuid] = data

    def start_psd(self):
        if not self.parameters.lock.value:
            return error_dialog(self, """Laser has to be locked for PSD measurement!""")

        self.control.start_psd_acquisition()

    def stop_psd(self):
        if self.parameters.task.value is not None:
            self.parameters.task.value.stop()
            self.parameters.task.value = None

    def start_pid_optimization(self):
        self.control.start_pid_optimization()

    def delete_curve(self):
        uuid = self.curveTable.delete_selected_curve()
        if uuid is not None:
            self.PSDPlot.delete_curve(uuid)
            del self.data[uuid]

    def export_psd(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".pickle"
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            f"PICKLE (*{default_ext})",
            options=options,
        )
        if fn:
            if not fn.endswith(default_ext):
                fn = fn + default_ext

            with open(fn, "wb") as f:
                pickle.dump(
                    {
                        "linien-version": linien_gui.__version__,
                        "time": time(),
                        "psd-data": self.data,
                    },
                    f,
                )

    def import_psd(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".pickle"
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            f"JSON (*{default_ext})",
            options=options,
        )
        if fn:
            with open(fn, "rb") as f:
                data = pickle.load(f)

            assert "linien-version" in data, "invalid parameter file"

            for uuid, psd_data in data["psd-data"].items():
                self.psd_data_received(pickle.dumps(psd_data))
