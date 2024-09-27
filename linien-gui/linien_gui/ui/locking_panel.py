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

from linien_common.enums import AutolockMode, AutolockStatus
from linien_gui.config import UI_PATH
from linien_gui.ui.spin_box import CustomSpinBox
from linien_gui.utils import get_linien_app_instance, param2ui, ui2param
from PyQt5 import QtCore, QtWidgets, uic

logger = logging.getLogger("linien_gui.ui.locking_panel")


class LockingPanel(QtWidgets.QWidget):
    kpSpinBox: CustomSpinBox
    kiSpinBox: CustomSpinBox
    kdSpinBox: CustomSpinBox
    slowPIDGroupBox: QtWidgets.QGroupBox
    pIDOnSlowStrengthSpinBox: CustomSpinBox
    autolockSelectingWidget: QtWidgets.QWidget
    abortSelectingPushButton: QtWidgets.QPushButton
    autolockSettingsWidget: QtWidgets.QWidget
    autoOffsetCheckbox: QtWidgets.QCheckBox
    autolockModePreferenceComboBox: QtWidgets.QComboBox
    selectLineToLockPushButton: QtWidgets.QPushButton
    manualModeWidget: QtWidgets.QWidget
    slopeFallingRadioButton: QtWidgets.QRadioButton
    slopeRisingRadioButton: QtWidgets.QRadioButton
    manualLockButton: QtWidgets.QPushButton
    resetLockFailedStatePushButton: QtWidgets.QPushButton
    lockStatusWidget: QtWidgets.QWidget
    controlSignalHistoryLengthSpinBox: CustomSpinBox
    lockStatusLabel: QtWidgets.QLabel
    stopLockPushButton: QtWidgets.QPushButton
    autolockAlgorithmGroupBox: QtWidgets.QGroupBox
    lockSettingsWidget: QtWidgets.QWidget
    manualLockSettingsWidget: QtWidgets.QWidget
    automaticLockSettingsWidget: QtWidgets.QWidget

    def __init__(self, *args, **kwargs):
        super(LockingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "locking_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.selectLineToLockPushButton.clicked.connect(self.start_autolock_selection)
        self.abortSelectingPushButton.clicked.connect(self.stop_autolock_selection)
        self.manualLockButton.clicked.connect(self.start_manual_lock)
        self.pIDOnSlowStrengthSpinBox.setKeyboardTracking(False)
        self.resetLockFailedStatePushButton.clicked.connect(self.reset_lock_failed)
        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        self.stopLockPushButton.clicked.connect(self.on_stop_lock)
        self.controlSignalHistoryLengthSpinBox.setKeyboardTracking(False)
        self.controlSignalHistoryLengthSpinBox.valueChanged.connect(
            self.on_control_signal_history_length_changed
        )

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.parameters.p, self.kpSpinBox)
        ui2param(self.kpSpinBox, self.parameters.p, control=self.control)
        param2ui(self.parameters.i, self.kiSpinBox)
        ui2param(self.kiSpinBox, self.parameters.i, control=self.control)
        param2ui(self.parameters.d, self.kdSpinBox)
        ui2param(self.kdSpinBox, self.parameters.d, control=self.control)
        ui2param(
            self.pIDOnSlowStrengthSpinBox,
            self.parameters.pid_on_slow_strength,
            control=self.control,
        )
        param2ui(self.parameters.autolock_determine_offset, self.autoOffsetCheckbox)
        ui2param(self.autoOffsetCheckbox, self.parameters.autolock_determine_offset)
        param2ui(self.parameters.pid_on_slow_strength, self.pIDOnSlowStrengthSpinBox)
        param2ui(
            self.parameters.control_signal_history_length,
            self.controlSignalHistoryLengthSpinBox,
        )
        self.parameters.pid_on_slow_enabled.add_callback(
            self.on_slow_pid_enabled_changed
        )
        param2ui(self.parameters.target_slope_rising, self.slopeRisingRadioButton)
        param2ui(
            self.parameters.target_slope_rising,
            self.slopeFallingRadioButton,
            lambda value: not value,
        )
        param2ui(
            self.parameters.autolock_mode_preference,
            self.autolockModePreferenceComboBox,
        )
        ui2param(
            self.autolockModePreferenceComboBox,
            self.parameters.autolock_mode_preference,
        )
        self.parameters.autolock_mode_preference.add_callback(
            self.on_autolock_mode_preference_changed
        )
        self.parameters.autolock_status.add_callback(self.on_autolock_status_changed)

    def on_autolock_status_changed(self, status: AutolockStatus) -> None:
        logger.debug(f"Autolock status changed to {status}")
        self.lockSettingsWidget.setVisible(status.value == AutolockStatus.STOPPED)
        self.resetLockFailedStatePushButton.setVisible(
            status.value == AutolockStatus.FAILED or status.value == AutolockStatus.LOST
        )
        self.autolockSelectingWidget.setVisible(
            status.value == AutolockStatus.SELECTING
        )
        self.lockStatusWidget.setVisible(
            status.value == AutolockStatus.LOCKED
            or status.value == AutolockStatus.LOCKING
            or status.value == AutolockStatus.LOST
        )
        match status.value:
            case AutolockStatus.LOCKED:
                self.lockStatusLabel.setText("Locked!")
            case AutolockStatus.LOCKING:
                self.lockStatusLabel.setText("Locking...")
            case AutolockStatus.LOST:
                self.lockStatusLabel.setText("Lock lost!")
            case _:
                self.lockStatusLabel.setText("Autolock status")

    def on_control_signal_history_length_changed(self):
        self.parameters.control_signal_history_length.value = (
            self.controlSignalHistoryLengthSpinBox.value()
        )

    def on_stop_lock(self):
        if self.parameters.task.value is not None:
            # this may be autolock or psd acquisition
            self.parameters.task.value.stop()
            self.parameters.task.value = None

    def on_slow_pid_enabled_changed(self, _) -> None:
        self.slowPIDGroupBox.setVisible(self.parameters.pid_on_slow_enabled.value)

    def on_autolock_mode_preference_changed(self, mode: AutolockMode) -> None:
        logger.debug(f"autolock_mode_preference changed to {mode}")
        self.manualLockSettingsWidget.setVisible(mode == AutolockMode.MANUAL)
        self.automaticLockSettingsWidget.setVisible(mode != AutolockMode.MANUAL)

    def start_manual_lock(self):
        self.control.exposed_start_autolock()

    def start_autolock_selection(self):
        self.parameters.autolock_status.value = AutolockStatus.SELECTING

    def stop_autolock_selection(self):
        self.parameters.autolock_status.value = AutolockStatus.STOPPED

    def reset_lock_failed(self):
        self.parameters.autolock_status.value = AutolockStatus.STOPPED
