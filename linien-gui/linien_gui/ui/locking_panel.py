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

from linien_common.common import AutolockMode, AutolockStatus
from linien_gui.config import UI_PATH
from linien_gui.ui.spin_box import CustomSpinBox
from linien_gui.utils import get_linien_app_instance, param2ui
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtCore import pyqtSignal


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

        self.parameters.lock.add_callback(self.update_status)
        self.parameters.task.add_callback(self.update_status)
        self.parameters.autolock_running.add_callback(self.update_status)
        self.parameters.autolock_failed.add_callback(self.update_status)
        self.parameters.autolock_locked.add_callback(self.update_status)
        self.parameters.autolock_retrying.add_callback(self.update_status)

        param2ui(
            self.parameters.control_signal_history_length,
            self.parent.controlSignalHistoryLengthSpinBox,
        )

    def on_lock_status_changed(self, status: AutolockStatus) -> None:
        match status:
            case AutolockStatus.LOCKED:
                self.show()
                self.parent.lockStatusLabel.setText("Locked!")
            case AutolockStatus.RUNNING:
                self.show()
                self.parent.lockStatusLabel.setText("Autolock is running...")
            case _:
                self.hide()

    def update_status(self, _) -> None:
        locked = self.parameters.lock.value
        task = self.parameters.task.value
        al_failed = self.parameters.autolock_failed.value
        running = self.parameters.autolock_running.value
        retrying = self.parameters.autolock_retrying.value

        if locked or (task is not None and not al_failed):
            self.show()
        else:
            self.hide()

        if not task:
            running = False

        def set_text(text):
            self.parent.lockStatusLabel.setText(text)

        if not running and locked:
            set_text("Locked!")
        if running and not locked:
            if not retrying:
                set_text("Autolock is running...")
            else:
                set_text("Trying again to lock...")

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
    lockControlTabWidget: QtWidgets.QTabWidget
    autolockSelectionActivedWidget: QtWidgets.QWidget
    abortLineSelectionPushButton: QtWidgets.QPushButton
    autolockSelectionNotActivedWidget: QtWidgets.QWidget
    autoOffsetCheckbox: QtWidgets.QCheckBox
    autolockModePreferenceComboBox: QtWidgets.QComboBox
    selectLineToLockPushButton: QtWidgets.QPushButton
    manualModeWidget: QtWidgets.QWidget
    slopeFallingRadioButton: QtWidgets.QRadioButton
    slopeRisingRadioButton: QtWidgets.QRadioButton
    manualLockButton: QtWidgets.QPushButton
    lockFailedWidget: QtWidgets.QWidget
    resetLockFailedStatePushButton: QtWidgets.QPushButton
    lockStatusWidget: LockStatusWidget
    controlSignalHistoryLengthSpinBox: CustomSpinBox
    lockStatusLabel: QtWidgets.QLabel
    stopLockPushButton: QtWidgets.QPushButton

    autolock_selection_signal = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        super(LockingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "locking_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)
        QtCore.QTimer.singleShot(100, self.ready)

        self.kpSpinBox.valueChanged.connect(self.on_kp_changed)
        self.kiSpinBox.valueChanged.connect(self.on_ki_changed)
        self.kdSpinBox.valueChanged.connect(self.on_kd_changed)
        self.lockControlTabWidget.currentChanged.connect(self.on_lock_mode_changed)
        self.selectLineToLockPushButton.clicked.connect(self.start_autolock_selection)
        self.abortLineSelectionPushButton.clicked.connect(self.stop_autolock_selection)
        self.manualLockButton.clicked.connect(self.start_manual_lock)
        self.autoOffsetCheckbox.stateChanged.connect(self.auto_offset_changed)
        self.pIDOnSlowStrengthSpinBox.setKeyboardTracking(False)
        self.pIDOnSlowStrengthSpinBox.valueChanged.connect(
            self.pid_on_slow_strength_changed
        )
        self.resetLockFailedStatePushButton.clicked.connect(self.reset_lock_failed)
        self.autolockModePreferenceComboBox.currentIndexChanged.connect(
            self.on_autolock_mode_preference_changed
        )
        self.autolock_selection_signal.connect(
            self.on_autolock_selection_status_changed
        )
        self.autolockSelectionActivedWidget.setVisible(False)
        self.autolockSelectionNotActivedWidget.setVisible(True)

    def ready(self) -> None:
        self.autolock_selection_signal.connect(
            self.app.main_window.plotWidget.on_autolock_selection_changed
        )

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.parameters.p, self.kpSpinBox)
        param2ui(self.parameters.i, self.kiSpinBox)
        param2ui(self.parameters.d, self.kdSpinBox)
        param2ui(self.parameters.autolock_determine_offset, self.autoOffsetCheckbox)
        param2ui(
            self.parameters.automatic_mode,
            self.lockControlTabWidget,
            lambda value: 0 if value else 1,
        )
        param2ui(self.parameters.pid_on_slow_strength, self.pIDOnSlowStrengthSpinBox)
        self.parameters.pid_on_slow_enabled.add_callback(self.on_slow_pid_changed)
        self.parameters.lock.add_callback(self.on_lock_status_changed)
        self.parameters.autolock_failed.add_callback(self.on_lock_status_changed)
        self.parameters.autolock_locked.add_callback(self.on_lock_status_changed)

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

    def on_lock_status_changed2(self, status: AutolockStatus) -> None:
        match status:
            case AutolockStatus.FAILED | AutolockStatus.LOCKED | AutolockStatus.RUNNING:
                self.lockControlTabWidget.hide()
            case _:
                self.lockControlTabWidget.show()
        self.lockFailedWidget.setVisible(status == AutolockStatus.FAILED)

    def on_lock_status_changed(self, _) -> None:
        locked = self.parameters.lock.value
        task = self.parameters.task.value
        al_failed = self.parameters.autolock_failed.value
        task_running = (task is not None) and (not al_failed)

        if locked or task_running or al_failed:
            self.lockControlTabWidget.hide()
        else:
            self.lockControlTabWidget.show()

        self.lockFailedWidget.setVisible(al_failed)

    def on_slow_pid_changed(self, _) -> None:
        self.slowPIDGroupBox.setVisible(self.parameters.pid_on_slow_enabled.value)

    def on_autolock_selection_status_changed(self, value: bool) -> None:
        self.autolockSelectionActivedWidget.setVisible(value)
        self.autolockSelectionNotActivedWidget.setVisible(not value)

    def on_kp_changed(self):
        self.parameters.p.value = self.kpSpinBox.value()
        self.control.write_registers()

    def on_ki_changed(self):
        self.parameters.i.value = self.kiSpinBox.value()
        self.control.write_registers()

    def on_kd_changed(self):
        self.parameters.d.value = self.kdSpinBox.value()
        self.control.write_registers()

    def on_lock_mode_changed(self, idx):
        self.parameters.automatic_mode.value = idx == 0

    def on_autolock_mode_preference_changed(self, idx):
        self.parameters.autolock_mode_preference.value = idx

    def start_manual_lock(self):
        self.parameters.target_slope_rising.value = (
            self.slopeRisingRadioButton.isChecked()
        )
        self.parameters.fetch_additional_signals.value = False
        self.parameters.autolock_mode.value = AutolockMode.SIMPLE
        self.parameters.autolock_target_position.value = 0
        self.control.write_registers()
        self.control.exposed_start_lock()

    def auto_offset_changed(self):
        self.parameters.autolock_determine_offset.value = int(
            self.autoOffsetCheckbox.checkState()
        )

    def pid_on_slow_strength_changed(self):
        self.parameters.pid_on_slow_strength.value = (
            self.pIDOnSlowStrengthSpinBox.value()
        )
        self.control.write_registers()

    def start_autolock_selection(self):
        self.autolock_selection_signal.emit(True)

    def stop_autolock_selection(self):
        self.autolock_selection_signal.emit(False)

    def reset_lock_failed(self):
        self.parameters.autolock_failed.value = False
