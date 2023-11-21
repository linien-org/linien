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

from linien_common.common import AutolockMode
from linien_gui.ui.lock_status_panel import LockStatusPanel
from linien_gui.ui.spin_box import CustomSpinBox
from linien_gui.utils import get_linien_app_instance, param2ui
from linien_gui.widgets import UI_PATH
from PyQt5 import QtWidgets, uic


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

    def __init__(self, *args, **kwargs):
        super(LockingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "locking_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.kpSpinBox.valueChanged.connect(self.kp_changed)
        self.kiSpinBox.valueChanged.connect(self.ki_changed)
        self.kdSpinBox.valueChanged.connect(self.kd_changed)
        self.lock_control_container.currentChanged.connect(self.lock_mode_changed)

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
            self.autolock_mode_preference_changed
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

        def slow_pid_visibility(*args):
            self.slow_pid_group.setVisible(self.parameters.pid_on_slow_enabled.value)

        self.parameters.pid_on_slow_enabled.add_callback(slow_pid_visibility)

        def lock_status_changed(_):
            locked = self.parameters.lock.value
            task = self.parameters.task.value
            al_failed = self.parameters.autolock_failed.value
            task_running = (task is not None) and (not al_failed)

            if locked or task_running or al_failed:
                self.lock_control_container.hide()
            else:
                self.lock_control_container.show()

            self.lock_failed.setVisible(al_failed)

        for param in (
            self.parameters.lock,
            self.parameters.autolock_preparing,
            self.parameters.autolock_watching,
            self.parameters.autolock_failed,
            self.parameters.autolock_locked,
        ):
            param.add_callback(lock_status_changed)

        param2ui(self.parameters.target_slope_rising, self.button_slope_rising)
        param2ui(
            self.parameters.target_slope_rising,
            self.button_slope_falling,
            lambda value: not value,
        )

        def autolock_selection_status_changed(value):
            self.auto_mode_activated.setVisible(value)
            self.auto_mode_not_activated.setVisible(not value)

        self.parameters.autolock_selection.add_callback(
            autolock_selection_status_changed
        )

        param2ui(
            self.parameters.autolock_mode_preference, self.autolock_mode_preference
        )

    def kp_changed(self):
        self.parameters.p.value = self.kpSpinBox.value()
        self.control.write_registers()

    def ki_changed(self):
        self.parameters.i.value = self.kiSpinBox.value()
        self.control.write_registers()

    def kd_changed(self):
        self.parameters.d.value = self.kdSpinBox.value()
        self.control.write_registers()

    def lock_mode_changed(self, idx):
        self.parameters.automatic_mode.value = idx == 0

    def autolock_mode_preference_changed(self, idx):
        self.parameters.autolock_mode_preference.value = idx

    def start_manual_lock(self):
        self.parameters.target_slope_rising.value = self.button_slope_rising.isChecked()
        self.parameters.fetch_additional_signals.value = False
        self.parameters.autolock_mode.value = AutolockMode.SIMPLE
        self.parameters.autolock_target_position.value = 0
        self.control.write_registers()
        self.control.start_lock()

    def auto_offset_changed(self):
        self.parameters.autolock_determine_offset.value = int(
            self.autoOffsetCheckbox.checkState()
        )

    def pid_on_slow_strength_changed(self):
        self.parameters.pid_on_slow_strength.value = self.pid_on_slow_strength.value()
        self.control.write_registers()

    def start_autolock_selection(self):
        self.parameters.autolock_selection.value = True

    def stop_autolock_selection(self):
        self.parameters.autolock_selection.value = False

    def reset_lock_failed(self):
        self.parameters.autolock_failed.value = False
