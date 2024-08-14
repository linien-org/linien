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
    error1LegendLabel: QtWidgets.QLabel
    error2LegendLabel: QtWidgets.QLabel
    monitorLegendLabel: QtWidgets.QLabel
    combinedErrorLegendLabel: QtWidgets.QLabel
    sweepControlWidget: SweepControlWidget
    sweepAmplitudeSpinBox: CustomDoubleSpinBox
    sweepCenterSpinBox: CustomDoubleSpinBox
    sweepSlider: SweepSlider
    sweepStartStopPushButton: QtWidgets.QPushButton
    topLockPanelWidget: QtWidgets.QWidget
    controlStdLabel: QtWidgets.QLabel
    errorStdLabel: QtWidgets.QLabel
    controlSignalLegendLabel: QtWidgets.QLabel
    controlSignalHistoryLegendLabel: QtWidgets.QLabel
    errorSignalLegendLabel: QtWidgets.QLabel
    monitorSignalHistoryLegendLabel: QtWidgets.QLabel
    slowSignalHistoryLegendLabel: QtWidgets.QLabel
    rightPanel: RightPanel
    exportParametersButton: QtWidgets.QPushButton
    importParametersButton: QtWidgets.QPushButton
    newVersionAvailableLabel: QtWidgets.QLabel
    PIDParameterOptimizationButton: QtWidgets.QPushButton
    settingsToolbox: QtWidgets.QToolBox
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
            lambda v: self.slowSignalHistoryLegendLabel.setVisible(v)
        )
        self.parameters.dual_channel.add_callback(
            lambda v: self.monitorSignalHistoryLegendLabel.setVisible(not v)
        )

        self.settingsToolbox.setCurrentIndex(0)

        self.parameters.lock.add_callback(lambda *args: self.reset_std_history())

        for color_idx in range(N_COLORS):
            getattr(self.app.settings, f"plot_color_{color_idx}").add_callback(
                self.on_plot_color_changed
            )

        self.parameters.dual_channel.add_callback(self.update_legend_text)

    def change_sweep_control_visibility(self, *args):
        al_running = self.parameters.autolock_running.value
        optimization = self.parameters.optimization_running.value
        locked = self.parameters.lock.value

        self.sweepControlWidget.setVisible(
            not al_running and not locked and not optimization
        )
        self.topLockPanelWidget.setVisible(locked)
        self.statusbar_unlocked.setVisible(
            not al_running and not locked and not optimization
        )

    def on_plot_color_changed(self, *args):
        def set_color(el, color: Color):
            return el.setStyleSheet(
                "color: "
                + color_to_hex(
                    getattr(self.app.settings, f"plot_color_{color.value}").value
                )
            )

        set_color(self.error1LegendLabel, Color.ERROR1)
        set_color(self.error2LegendLabel, Color.ERROR2)
        set_color(self.monitorLegendLabel, Color.MONITOR)
        set_color(self.combinedErrorLegendLabel, Color.ERROR_COMBINED)
        set_color(self.errorSignalLegendLabel, Color.ERROR_COMBINED)
        set_color(self.controlSignalLegendLabel, Color.CONTROL_SIGNAL)
        set_color(self.controlSignalHistoryLegendLabel, Color.CONTROL_SIGNAL_HISTORY)
        set_color(self.slowSignalHistoryLegendLabel, Color.SLOW_HISTORY)
        set_color(self.monitorSignalHistoryLegendLabel, Color.MONITOR_SIGNAL_HISTORY)

    def update_legend_text(self, dual_channel: bool) -> None:
        self.error1LegendLabel.setVisible(dual_channel)
        self.error2LegendLabel.setVisible(dual_channel)
        self.monitorLegendLabel.setVisible(not dual_channel)
        self.combinedErrorLegendLabel.setText(
            "error" if not dual_channel else "combined error"
        )

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
                    self.errorStdLabel.setText(f"{np.mean(self.error_std_history):.2f}")
                    self.controlStdLabel.setText(
                        f"{np.mean(self.control_std_history):.2f}"
                    )

    def reset_std_history(self):
        self.error_std_history = []
        self.control_std_history = []
