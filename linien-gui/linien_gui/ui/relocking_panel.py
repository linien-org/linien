# Copyright 2024 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien.
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

from linien_gui.config import UI_PATH
from linien_gui.ui.spin_box import CustomDoubleSpinBoxNoSign
from linien_gui.utils import get_linien_app_instance, param2ui, ui2param
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RelockingPanel(QtWidgets.QWidget):
    automaticRelockingCheckbox: QtWidgets.QCheckBox
    watchLockCheckBox: QtWidgets.QCheckBox
    watchLockOnControlChannelCheckBox: QtWidgets.QCheckBox
    watchLockOnControlChannelMinSpinBox: CustomDoubleSpinBoxNoSign
    watchLockOnControlChannelMaxSpinBox: CustomDoubleSpinBoxNoSign
    watchLockOnErrorChannelCheckBox: QtWidgets.QCheckBox
    watchLockOnErrorChannelMinSpinBox: CustomDoubleSpinBoxNoSign
    watchLockOnErrorChannelMaxSpinBox: CustomDoubleSpinBoxNoSign
    watchLockOnMonitorChannelCheckBox: QtWidgets.QCheckBox
    watchLockOnMonitorChannelMinSpinBox: CustomDoubleSpinBoxNoSign
    watchLockOnMonitorChannelMaxSpinBox: CustomDoubleSpinBoxNoSign
    plotControlSignalThresholdCheckBox: QtWidgets.QCheckBox
    plotErrorSignalThresholdCheckBox: QtWidgets.QCheckBox
    plotMonitorSignalThresholdCheckBox: QtWidgets.QCheckBox

    control_signal_thresholds = pyqtSignal(bool, float, float)
    error_signal_thresholds = pyqtSignal(bool, float, float)
    monitor_signal_thresholds = pyqtSignal(bool, float, float)

    def __init__(self, *args, **kwargs) -> None:
        super(RelockingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "relocking_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

    def on_connection_established(self) -> None:
        self.parameters = self.app.parameters
        self.settings = self.app.settings
        self.control = self.app.control

        # Connect parameters and GUI controls and vice-versa:
        # Watch and relock checkboxes
        self.parameters.watch_lock.add_callback(self.disable_relocking_checkbox)

        ui2param(
            self.watchLockCheckBox, self.parameters.watch_lock, control=self.control
        )
        param2ui(self.parameters.watch_lock, self.watchLockCheckBox)

        ui2param(
            self.automaticRelockingCheckbox,
            self.parameters.automatic_relocking,
            control=self.control,
        )
        param2ui(self.parameters.automatic_relocking, self.automaticRelockingCheckbox)
        # Control signal stuff:
        ui2param(
            self.plotControlSignalThresholdCheckBox,
            self.settings.show_control_threshold,
        )
        param2ui(
            self.settings.show_control_threshold,
            self.plotControlSignalThresholdCheckBox,
        )
        ui2param(
            self.watchLockOnControlChannelMinSpinBox,
            self.parameters.watch_lock_control_min,
            process_value=lambda x: x / 100,
            control=self.control,
        )
        param2ui(
            self.parameters.watch_lock_control_min,
            self.watchLockOnControlChannelMinSpinBox,
            process_value=lambda x: 100 * x,
        )
        ui2param(
            self.watchLockOnControlChannelMaxSpinBox,
            self.parameters.watch_lock_control_max,
            process_value=lambda x: x / 100,
            control=self.control,
        )
        param2ui(
            self.parameters.watch_lock_control_max,
            self.watchLockOnControlChannelMaxSpinBox,
            process_value=lambda x: 100 * x,
        )
        # Error signal stuff:
        ui2param(
            self.plotControlSignalThresholdCheckBox,
            self.settings.show_error_threshold,
        )
        param2ui(
            self.settings.show_error_threshold,
            self.plotErrorSignalThresholdCheckBox,
        )
        ui2param(
            self.watchLockOnErrorChannelMinSpinBox,
            self.parameters.watch_error_control_min,
            process_value=lambda x: x / 100,
            control=self.control,
        )
        param2ui(
            self.parameters.watch_lock_error_min,
            self.watchLockOnErrorChannelMinSpinBox,
            lambda x: 100 * x,
        )
        ui2param(
            self.watchLockOnErrorChannelMaxSpinBox,
            self.on_watch_lock_error_max_changed,
            process_value=lambda x: x / 100,
            control=self.control,
        )
        param2ui(
            self.parameters.watch_lock_error_max,
            self.watchLockOnErrorChannelMaxSpinBox,
            lambda x: 100 * x,
        )
        # Monitor signal stuff:
        ui2param(
            self.plotMonitorSignalThresholdCheckBox,
            self.on_monitor_thresholds_changed,
        )
        param2ui(
            self.settings.show_monitor_threshold,
            self.plotMonitorSignalThresholdCheckBox,
        )
        ui2param(
            self.watchLockOnMonitorChannelMinSpinBox,
            self.parameters.watch_lock_monitor_min,
            process_value=lambda x: x / 100,
            control=self.control,
        )
        param2ui(
            self.parameters.watch_lock_monitor_min,
            self.watchLockOnControlChannelMinSpinBox,
            lambda x: 100 * x,
        )
        ui2param(
            self.watchLockOnMonitorChannelMaxSpinBox,
            self.parameters.watch_lock_monitor_max,
            process_value=lambda x: x / 100,
            control=self.control,
        )
        param2ui(
            self.parameters.watch_lock_monitor_max,
            self.watchLockOnMonitorChannelMaxSpinBox,
            lambda x: 100 * x,
        )

        # Connect changed parameter settings to plot widget:
        # Control thresholds:
        for param in (
            self.settings.show_control_threshold,
            self.parameters.watch_lock_control_min,
            self.parameters.watch_lock_control_max,
        ):
            param.add_callback(self.on_control_thresholds_changed)
        self.control_signal_thresholds.connect(
            self.app.main_window.graphicsView.show_control_thresholds
        )

        # Error thresholds:
        for param in (
            self.settings.show_error_threshold,
            self.parameters.watch_lock_error_min,
            self.parameters.watch_lock_error_max,
        ):
            param.add_callback(self.on_error_thresholds_changed)
        self.error_signal_thresholds.connect(
            self.app.main_window.graphicsView.show_error_thresholds
        )

        # Monitor thresholds:
        for param in (
            self.settings.show_monitor_threshold,
            self.parameters.watch_lock_monitor_min,
            self.parameters.watch_lock_monitor_max,
        ):
            param.add_callback(self.on_monitor_thresholds_changed)
            print("added callback")
        self.monitor_signal_thresholds.connect(
            self.app.main_window.graphicsView.show_monitor_thresholds
        )

    def disable_relocking_checkbox(self, watch_lock_enabled: bool) -> None:
        """Disable relocking checkbox if watch lock is not enabled."""
        self.automaticRelockingCheckbox.setEnabled(watch_lock_enabled)

    def on_control_thresholds_changed(self) -> None:
        print("control thresholds changed")
        self.control_signal_thresholds.emit(
            self.settings.show_control_threshold,
            self.parameters.watch_lock_control_min.value,
            self.parameters.watch_lock_control_max.value,
        )

    def on_error_thresholds_changed(self) -> None:
        self.control_signal_thresholds.emit(
            self.settings.show_error_threshold,
            self.parameters.watch_lock_error_min.value,
            self.parameters.watch_lock_error_max.value,
        )

    def on_monitor_thresholds_changed(self) -> None:
        self.monitor_signal_thresholds.emit(
            self.settings.show_monitor_threshold,
            self.parameters.watch_lock_monitor_min.value,
            self.parameters.watch_lock_monitor_max.value,
        )
