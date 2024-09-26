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


class LockStatusWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(LockStatusWidget, self).__init__(*args, **kwargs)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)
        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        self.parent: LockingPanel = self.parent()
        self.parent.stopLockPushButton.clicked.connect(self.on_stop_lock)
        self.parent.controlSignalHistoryLengthSpinBox.setKeyboardTracking(False)
        self.parent.controlSignalHistoryLengthSpinBox.valueChanged.connect(
            self.on_control_signal_history_length_changed
        )

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        self.parameters.autolock_status.add_callback(self.on_lock_status_changed)

        param2ui(
            self.parameters.control_signal_history_length,
            self.parent.controlSignalHistoryLengthSpinBox,
        )

    def on_lock_status_changed(self, status: AutolockStatus) -> None:
        match status.value:
            case AutolockStatus.LOCKED:
                self.show()
                self.parent.lockStatusLabel.setText("Locked!")
            case AutolockStatus.LOCKING:
                self.show()
                self.parent.lockStatusLabel.setText("Autolock is running...")
            case _:
                self.hide()

    def on_stop_lock(self):
        self.parameters.fetch_additional_signals.value = True

        if self.parameters.task.value is not None:
            # this may be autolock or psd acquisition
            self.parameters.task.value.stop()
            self.parameters.task.value = None

        self.control.exposed_start_sweep()

    def on_control_signal_history_length_changed(self):
        self.parameters.control_signal_history_length.value = (
            self.parent.controlSignalHistoryLengthSpinBox.value()
        )


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
    lockStatusWidget: LockStatusWidget
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

        self.kpSpinBox.valueChanged.connect(self.on_kp_changed)
        self.kiSpinBox.valueChanged.connect(self.on_ki_changed)
        self.kdSpinBox.valueChanged.connect(self.on_kd_changed)
        self.selectLineToLockPushButton.clicked.connect(self.start_autolock_selection)
        self.abortSelectingPushButton.clicked.connect(self.stop_autolock_selection)
        self.manualLockButton.clicked.connect(self.start_manual_lock)
        self.autoOffsetCheckbox.stateChanged.connect(self.auto_offset_changed)
        self.pIDOnSlowStrengthSpinBox.setKeyboardTracking(False)
        self.pIDOnSlowStrengthSpinBox.valueChanged.connect(
            self.pid_on_slow_strength_changed
        )
        self.resetLockFailedStatePushButton.clicked.connect(self.reset_lock_failed)

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        self.parameters.autolock_status.add_callback(self.on_autolock_status_changed)

        param2ui(self.parameters.p, self.kpSpinBox)
        param2ui(self.parameters.i, self.kiSpinBox)
        param2ui(self.parameters.d, self.kdSpinBox)
        param2ui(self.parameters.autolock_determine_offset, self.autoOffsetCheckbox)
        param2ui(self.parameters.pid_on_slow_strength, self.pIDOnSlowStrengthSpinBox)

        self.parameters.autolock_status.add_callback(self.on_autolock_status_changed)

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

    def on_autolock_status_changed(self, status: AutolockStatus) -> None:
        logger.debug(f"Autolock status changed to {status}")
        self.lockSettingsWidget.setVisible(status.value == AutolockStatus.STOPPED)
        self.resetLockFailedStatePushButton.setVisible(
            status.value == AutolockStatus.FAILED
        )
        self.autolockSelectingWidget.setVisible(
            status.value == AutolockStatus.SELECTING
        )

    def on_slow_pid_changed(self, _) -> None:
        self.slowPIDGroupBox.setVisible(self.parameters.pid_on_slow_enabled.value)

    def on_kp_changed(self):
        self.parameters.p.value = self.kpSpinBox.value()
        self.control.write_registers()

    def on_ki_changed(self):
        self.parameters.i.value = self.kiSpinBox.value()
        self.control.write_registers()

    def on_kd_changed(self):
        self.parameters.d.value = self.kdSpinBox.value()
        self.control.write_registers()

    def on_autolock_mode_preference_changed(self, mode: AutolockMode) -> None:
        logger.debug(f"autolock_mode_preference changed to {mode}")
        self.manualLockSettingsWidget.setVisible(mode == AutolockMode.MANUAL)
        self.automaticLockSettingsWidget.setVisible(mode != AutolockMode.MANUAL)

    def start_manual_lock(self):
        self.control.exposed_start_autolock()

    def auto_offset_changed(self):
        self.parameters.autolock_determine_offset.value = bool(
            self.autoOffsetCheckbox.checkState()
        )

    def pid_on_slow_strength_changed(self):
        self.parameters.pid_on_slow_strength.value = (
            self.pIDOnSlowStrengthSpinBox.value()
        )
        self.control.write_registers()

    def start_autolock_selection(self):
        self.parameters.autolock_status.value = AutolockStatus.SELECTING

    def stop_autolock_selection(self):
        self.parameters.autolock_status.value = AutolockStatus.STOPPED

    def reset_lock_failed(self):
        self.parameters.autolock_status.value = AutolockStatus.STOPPED
