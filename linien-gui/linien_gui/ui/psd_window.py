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

import pickle
from time import time

import linien_gui
from linien_common.common import PSD_ALGORITHM_LPSD, PSD_ALGORITHM_WELCH
from linien_gui.dialogs import error_dialog
from linien_gui.utils_gui import RandomColorChoser, param2ui, set_window_icon
from linien_gui.widgets import CustomWidget
from PyQt5 import QtWidgets


class PSDWindow(QtWidgets.QMainWindow, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("psd_window.ui")
        self.setWindowTitle("Linien: Noise analysis")
        set_window_icon(self)
        self.random_color_choser = RandomColorChoser()
        self.colors = {}
        self.data = {}
        self.complete_uids = []

    def ready(self):
        self.ids.start_psd_button.clicked.connect(self.start_psd)
        """self.ids.start_pid_optimization_button.clicked.connect(
            self.start_pid_optimization
        )"""
        self.ids.stop_psd_button.clicked.connect(self.stop_psd)

        self.ids.curve_table.show_or_hide_curve.connect(
            self.ids.psd_plot_widget.show_or_hide_curve
        )
        self.ids.delete_curve_button.clicked.connect(self.delete_curve)
        self.ids.export_psd_button.clicked.connect(self.export_psd)
        self.ids.import_psd_button.clicked.connect(self.import_psd)

        self.ids.maximum_measurement_time.currentIndexChanged.connect(
            self.change_maximum_measurement_time
        )

        self.ids.psd_algorithm.currentIndexChanged.connect(self.change_psd_algorithm)

    def closeEvent(self, event, *args, **kwargs):
        # we never realy want to close the window (which destroys its content)
        # but just to hide it
        event.ignore()
        self.hide()

    def change_maximum_measurement_time(self, index):
        self.parameters.psd_acquisition_max_decimation.value = 12 + index

    def change_psd_algorithm(self, index):
        self.parameters.psd_algorithm.value = [PSD_ALGORITHM_LPSD, PSD_ALGORITHM_WELCH][
            index
        ]

    def connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        self.parameters.psd_data_partial.on_change(
            self.psd_data_received,
        )
        self.parameters.psd_data_complete.on_change(
            self.psd_data_received,
        )

        param2ui(
            self.parameters.psd_acquisition_max_decimation,
            self.ids.maximum_measurement_time,
            lambda max_decimation: max_decimation - 12,
        )
        param2ui(
            self.parameters.psd_algorithm,
            self.ids.psd_algorithm,
            lambda algo: {PSD_ALGORITHM_LPSD: 0, PSD_ALGORITHM_WELCH: 1}[algo],
        )

        def update_status(_):
            psd_running = self.parameters.psd_acquisition_running.value
            if psd_running:
                self.ids.container_psd_running.show()
                self.ids.container_psd_not_running.hide()
            else:
                self.ids.container_psd_running.hide()
                self.ids.container_psd_not_running.show()

        self.parameters.psd_acquisition_running.on_change(update_status)

    def psd_data_received(self, data_pickled):
        if data_pickled is None:
            return

        data = pickle.loads(data_pickled)

        curve_uuid = data["uuid"]

        if curve_uuid in self.complete_uids:
            # in networks with high latency it may happen that psd data is not
            # received in order. We do not want to update a complete plot with
            # a partial one --> stop here
            return

        if data["complete"]:
            self.complete_uids.append(curve_uuid)

        # either re-use the color of the previous partial plot of this curve
        # or generate a new color if the curve was not yet partially plotted
        if curve_uuid not in self.colors:
            color = self.random_color_choser.get()
            self.colors[curve_uuid] = color
        else:
            color = self.colors[curve_uuid]

        self.ids.psd_plot_widget.plot_curve(curve_uuid, data["psds"], color)
        self.ids.curve_table.add_curve(curve_uuid, data, color)

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
        uuid = self.ids.curve_table.delete_selected_curve()
        if uuid is not None:
            self.ids.psd_plot_widget.delete_curve(uuid)
            del self.data[uuid]

    def export_psd(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".pickle"
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            "PICKLE (*%s)" % default_ext,
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
            "JSON (*%s)" % default_ext,
            options=options,
        )
        if fn:
            with open(fn, "rb") as f:
                data = pickle.load(f)

            assert "linien-version" in data, "invalid parameter file"

            for uuid, psd_data in data["psd-data"].items():
                self.psd_data_received(pickle.dumps(psd_data))
