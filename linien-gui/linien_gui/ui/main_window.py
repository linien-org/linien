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

import logging
import pickle
from math import log

import linien_gui
import numpy as np
from linien_client.device import add_device, load_device, update_device
from linien_common.common import check_plot_data
from linien_gui.config import N_COLORS, UI_PATH, Color
from linien_gui.ui.plot_widget import INVALID_POWER
from linien_gui.ui.right_panel import RightPanel
from linien_gui.ui.spin_box import CustomDoubleSpinBox
from linien_gui.ui.sweep_control import SweepControlWidget, SweepSlider
from linien_gui.utils import color_to_hex, get_linien_app_instance, set_window_icon
from PyQt5 import QtWidgets, uic

ZOOM_STEP = 0.9
MAX_ZOOM = 50
MIN_ZOOM = 0

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def sweep_amplitude_to_zoom_step(amplitude):
    return round(log(amplitude, ZOOM_STEP))


class MainWindow(QtWidgets.QMainWindow):
    statusbar_unlocked: QtWidgets.QWidget
    signal_strenghts_unlocked: QtWidgets.QHBoxLayout
    power_channel_1: QtWidgets.QLabel
    power_channel_2: QtWidgets.QLabel
    legend_unlocked: QtWidgets.QHBoxLayout
    legend_spectrum_1: QtWidgets.QLabel
    legend_spectrum_2: QtWidgets.QLabel
    legend_spectrum_combined: QtWidgets.QLabel
    sweepControlWidget: SweepControlWidget
    sweepAmplitudeSpinBox: CustomDoubleSpinBox
    sweepCenterSpinBox: CustomDoubleSpinBox
    sweepSlider: SweepSlider
    sweepStartStopPushButton: QtWidgets.QPushButton
    top_lock_panel: QtWidgets.QWidget
    control_std: QtWidgets.QLabel
    error_std: QtWidgets.QLabel
    legend_control_signal: QtWidgets.QLabel
    legend_control_signal_history: QtWidgets.QLabel
    legend_error_signal: QtWidgets.QLabel
    legend_monitor_signal_history: QtWidgets.QLabel
    legend_slow_signal_history: QtWidgets.QLabel
    rightPanel: RightPanel
    exportParametersButton: QtWidgets.QPushButton
    importParametersButton: QtWidgets.QPushButton
    newVersionAvailableLabel: QtWidgets.QLabel
    pid_parameter_optimization_button: QtWidgets.QPushButton
    settings_toolbox: QtWidgets.QToolBox
    generalPanel: QtWidgets.QWidget
    modSpectroscopyPanel: QtWidgets.QWidget
    optimizationPanel: QtWidgets.QWidget
    loggingPanel: QtWidgets.QWidget
    viewPanel: QtWidgets.QWidget
    lockingPanel: QtWidgets.QWidget
    shutdownButton: QtWidgets.QPushButton
    closeButton: QtWidgets.QPushButton
    openDeviceManagerButton: QtWidgets.QPushButton

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "main_window.ui", self)
        set_window_icon(self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.reset_std_history()

        # handle keyboard events
        self.setFocus()

        self.exportParametersButton.clicked.connect(self.export_parameters)
        self.importParametersButton.clicked.connect(self.import_parameters)

        def display_power(power, element):
            if power == INVALID_POWER:
                element.hide()
            else:
                element.show()
                element.setText(f"{power:.2f}")

        def display_power_channel_1(power):
            el = self.power_channel_1
            display_power(power, el)

        def display_power_channel_2(power):
            el = self.power_channel_2
            display_power(power, el)

        self.graphicsView.signal_power1.connect(display_power_channel_1)
        self.graphicsView.signal_power2.connect(display_power_channel_2)
        self.graphicsView.keyPressed.connect(self.handle_key_press)

        # by default we hide it and just show when a new version is available
        self.newVersionAvailableLabel.hide()

    def on_connection_established(self):
        self.control = self.app.control
        self.parameters = self.app.parameters

        self.parameters.lock.add_callback(self.change_sweep_control_visibility)
        self.parameters.autolock_running.add_callback(
            self.change_sweep_control_visibility
        )
        self.parameters.optimization_running.add_callback(
            self.change_sweep_control_visibility
        )

        self.parameters.to_plot.add_callback(self.update_std)

        self.parameters.pid_on_slow_enabled.add_callback(
            lambda v: self.legend_slow_signal_history.setVisible(v)
        )
        self.parameters.dual_channel.add_callback(
            lambda v: self.legend_monitor_signal_history.setVisible(not v)
        )

        self.settings_toolbox.setCurrentIndex(0)

        self.parameters.lock.add_callback(lambda *args: self.reset_std_history())

        for color_idx in range(N_COLORS):
            getattr(self.app.settings, f"plot_color_{color_idx}").add_callback(
                self.update_legend_color
            )

        self.parameters.dual_channel.add_callback(self.update_legend_text)

    def change_sweep_control_visibility(self, *args):
        al_running = self.parameters.autolock_running.value
        optimization = self.parameters.optimization_running.value
        locked = self.parameters.lock.value

        self.sweepControlWidget.setVisible(
            not al_running and not locked and not optimization
        )
        self.top_lock_panel.setVisible(locked)
        self.statusbar_unlocked.setVisible(
            not al_running and not locked and not optimization
        )

    def update_legend_color(self, *args):
        def set_color(el, color: Color):
            return el.setStyleSheet(
                "color: "
                + color_to_hex(
                    getattr(self.app.settings, f"plot_color_{color.value}").value
                )
            )

        set_color(self.legend_spectrum_1, Color.SPECTRUM1)
        set_color(self.legend_spectrum_2, Color.SPECTRUM2)
        set_color(self.legend_spectrum_combined, Color.SPECTRUM_COMBINED)
        set_color(self.legend_error_signal, Color.SPECTRUM_COMBINED)
        set_color(self.legend_control_signal, Color.CONTROL_SIGNAL)
        set_color(self.legend_control_signal_history, Color.CONTROL_SIGNAL_HISTORY)
        set_color(self.legend_slow_signal_history, Color.SLOW_HISTORY)
        set_color(self.legend_monitor_signal_history, Color.MONITOR_SIGNAL_HISTORY)

    def update_legend_text(self, dual_channel):
        self.legend_spectrum_1.setText(
            "error signal" if not dual_channel else "error signal 1"
        )
        self.legend_spectrum_2.setText(
            "monitor" if not dual_channel else "error signal 2"
        )
        self.legend_spectrum_combined.setVisible(dual_channel)

    def show(self, host: str, name: str) -> None:  # type: ignore[override]
        self.setWindowTitle(
            f"Linien spectroscopy lock {linien_gui.__version__}: {name} ({host})"
        )
        super().show()

    def closeEvent(self, *args, **kwargs):
        self.app.close_all_secondary_windows()
        super().closeEvent(*args, **kwargs)

    def show_new_version_available(self):
        self.newVersionAvailableLabel.show()

    def handle_key_press(self, key):
        logger.debug(f"key pressed {key}")

    def export_parameters(self):
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

            try:
                add_device(self.app.client.device, path=fn)
            except KeyError:
                logger.warning(
                    f"Device with key {self.app.client.device.key} already exists in"
                    f"{fn}. Updating the device instead."
                )
                update_device(self.app.client.device, path=fn)

    def import_parameters(self):
        options = QtWidgets.QFileDialog.Options()
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            "JSON (*.json)",
            options=options,
        )
        if fn:
            try:
                self.app.client.device = load_device(
                    self.app.client.device.key, path=fn
                )
                for name, value in self.app.client.device.parameters.items():
                    param = getattr(self.app.client.parameters, name)
                    param.value = value
                self.control.exposed_write_registers()
            except KeyError:
                logger.error("Unable to load device from file. Key doesn't exist.")

    def update_std(self, to_plot, max_std_history_length=10):
        if self.parameters.lock.value and to_plot:
            to_plot = pickle.loads(to_plot)
            if to_plot and check_plot_data(True, to_plot):
                error_signal = to_plot.get("error_signal")
                control_signal = to_plot.get("control_signal")

                self.error_std_history.append(np.std(error_signal))
                self.control_std_history.append(np.std(control_signal))

                self.error_std_history = self.error_std_history[
                    -max_std_history_length:
                ]
                self.control_std_history = self.control_std_history[
                    -max_std_history_length:
                ]

                if error_signal is not None and control_signal is not None:
                    self.error_std.setText(f"{np.mean(self.error_std_history):.2f}")
                    self.control_std.setText(f"{np.mean(self.control_std_history):.2f}")

    def reset_std_history(self):
        self.error_std_history = []
        self.control_std_history = []
