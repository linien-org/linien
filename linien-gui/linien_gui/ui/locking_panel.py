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

from linien_common.common import AutolockMode
from linien_gui.config import UI_PATH
from linien_gui.ui.lock_status_panel import LockStatusPanel
from linien_gui.ui.spin_box import CustomSpinBox
from linien_gui.utils import get_linien_app_instance, param2ui
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtCore import pyqtSignal


class LockingPanel(QtWidgets.QWidget):
    kpSpinBox: CustomSpinBox
    kiSpinBox: CustomSpinBox
    kdSpinBox: CustomSpinBox
    slow_pid_group: QtWidgets.QGroupBox
    pid_on_slow_strength: CustomSpinBox
    lock_control_container: QtWidgets.QTabWidget
    auto_mode_activated: QtWidgets.QWidget
    abortLineSelection: QtWidgets.QPushButton
    auto_mode_not_activated: QtWidgets.QWidget
    autoOffsetCheckbox: QtWidgets.QCheckBox
    autolock_mode_preference: QtWidgets.QComboBox
    selectLineToLock: QtWidgets.QPushButton
    manual_mode: QtWidgets.QWidget
    button_slope_falling: QtWidgets.QRadioButton
    button_slope_rising: QtWidgets.QRadioButton
    manualLockButton: QtWidgets.QPushButton
    lock_failed: QtWidgets.QWidget
    reset_lock_failed_state: QtWidgets.QPushButton
    lock_status_container: LockStatusPanel
    controlSignalHistoryLengthSpinBox: CustomSpinBox
    lock_status: QtWidgets.QLabel
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
        self.lock_control_container.currentChanged.connect(self.on_lock_mode_changed)
        self.selectLineToLock.clicked.connect(self.start_autolock_selection)
        self.abortLineSelection.clicked.connect(self.stop_autolock_selection)
        self.manualLockButton.clicked.connect(self.start_manual_lock)
        self.autoOffsetCheckbox.stateChanged.connect(self.auto_offset_changed)
        self.pid_on_slow_strength.setKeyboardTracking(False)
        self.pid_on_slow_strength.valueChanged.connect(
            self.pid_on_slow_strength_changed
        )
        self.reset_lock_failed_state.clicked.connect(self.reset_lock_failed)
        self.autolock_mode_preference.currentIndexChanged.connect(
            self.on_autolock_mode_preference_changed
        )
        self.autolock_selection_signal.connect(
            self.on_autolock_selection_status_changed
        )

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
            self.lock_control_container,
            lambda value: 0 if value else 1,
        )
        param2ui(self.parameters.pid_on_slow_strength, self.pid_on_slow_strength)
        self.parameters.pid_on_slow_enabled.add_callback(self.on_slow_pid_changed)
        self.parameters.lock.add_callback(self.on_lock_status_changed)
        self.parameters.autolock_preparing.add_callback(self.on_lock_status_changed)
        self.parameters.autolock_failed.add_callback(self.on_lock_status_changed)
        self.parameters.autolock_locked.add_callback(self.on_lock_status_changed)

        param2ui(self.parameters.target_slope_rising, self.button_slope_rising)
        param2ui(
            self.parameters.target_slope_rising,
            self.button_slope_falling,
            lambda value: not value,
        )
        param2ui(
            self.parameters.autolock_mode_preference, self.autolock_mode_preference
        )

    def on_lock_status_changed(self, _):
        locked = self.parameters.lock.value
        task = self.parameters.task.value
        al_failed = self.parameters.autolock_failed.value
        task_running = (task is not None) and (not al_failed)

        if locked or task_running or al_failed:
            self.lock_control_container.hide()
        else:
            self.lock_control_container.show()

        self.lock_failed.setVisible(al_failed)

    def on_slow_pid_changed(self, _) -> None:
        self.slow_pid_group.setVisible(self.parameters.pid_on_slow_enabled.value)

    def on_autolock_selection_status_changed(self, value: bool) -> None:
        self.auto_mode_activated.setVisible(value)
        self.auto_mode_not_activated.setVisible(not value)

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
        self.parameters.target_slope_rising.value = self.button_slope_rising.isChecked()
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
        self.parameters.pid_on_slow_strength.value = self.pid_on_slow_strength.value()
        self.control.write_registers()

    def start_autolock_selection(self):
        self.autolock_selection_signal.emit(True)

    def stop_autolock_selection(self):
        self.autolock_selection_signal.emit(False)

    def reset_lock_failed(self):
        self.parameters.autolock_failed.value = False
