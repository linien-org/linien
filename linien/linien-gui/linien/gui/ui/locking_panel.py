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

from PyQt5 import QtWidgets

from linien.common import FAST_AUTOLOCK
from linien.gui.utils_gui import param2ui
from linien.gui.widgets import CustomWidget


class LockingPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("locking_panel.ui")

    def ready(self):
        self.ids.kp.valueChanged.connect(self.kp_changed)
        self.ids.ki.valueChanged.connect(self.ki_changed)
        self.ids.kd.valueChanged.connect(self.kd_changed)
        # self.ids.checkLockCheckbox.stateChanged.connect(self.check_lock_changed)
        # self.ids.watchLockCheckbox.stateChanged.connect(self.watch_lock_changed)
        # self.ids.watch_lock_threshold.valueChanged.connect(
        #    self.watch_lock_threshold_changed
        # )
        self.ids.lock_control_container.currentChanged.connect(self.lock_mode_changed)

        self.ids.selectLineToLock.clicked.connect(self.start_autolock_selection)
        self.ids.abortLineSelection.clicked.connect(self.stop_autolock_selection)

        self.ids.manualLockButton.clicked.connect(self.start_manual_lock)
        self.ids.autoOffsetCheckbox.stateChanged.connect(self.auto_offset_changed)

        self.ids.pid_on_slow_strength.setKeyboardTracking(False)
        self.ids.pid_on_slow_strength.valueChanged.connect(
            self.pid_on_slow_strength_changed
        )

        self.ids.reset_lock_failed_state.clicked.connect(self.reset_lock_failed)

        self.ids.autolock_mode_preference.currentIndexChanged.connect(
            self.autolock_mode_preference_changed
        )

    def connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.parameters.p, self.ids.kp)
        param2ui(self.parameters.i, self.ids.ki)
        param2ui(self.parameters.d, self.ids.kd)

        # param2ui(params.check_lock, self.ids.checkLockCheckbox)
        # param2ui(params.watch_lock, self.ids.watchLockCheckbox)
        # param2ui(
        #    params.watch_lock_threshold,
        #    self.ids.watch_lock_threshold,
        #    lambda v: v * 100,
        # )
        param2ui(self.parameters.autolock_determine_offset, self.ids.autoOffsetCheckbox)
        param2ui(
            self.parameters.automatic_mode,
            self.ids.lock_control_container,
            lambda value: 0 if value else 1,
        )
        param2ui(self.parameters.pid_on_slow_strength, self.ids.pid_on_slow_strength)

        def slow_pid_visibility(*args):
            self.ids.slow_pid_group.setVisible(
                self.parameters.pid_on_slow_enabled.value
            )

        self.parameters.pid_on_slow_enabled.on_change(slow_pid_visibility)

        def lock_status_changed(_):
            locked = self.parameters.lock.value
            task = self.parameters.task.value
            al_failed = self.parameters.autolock_failed.value
            task_running = (task is not None) and (not al_failed)

            if locked or task_running or al_failed:
                self.ids.lock_control_container.hide()
            else:
                self.ids.lock_control_container.show()

            self.ids.lock_failed.setVisible(al_failed)

        for param in (
            self.parameters.lock,
            self.parameters.autolock_preparing,
            self.parameters.autolock_watching,
            self.parameters.autolock_failed,
            self.parameters.autolock_locked,
        ):
            param.on_change(lock_status_changed)

        param2ui(self.parameters.target_slope_rising, self.ids.button_slope_rising)
        param2ui(
            self.parameters.target_slope_rising,
            self.ids.button_slope_falling,
            lambda value: not value,
        )

        def autolock_selection_status_changed(value):
            self.ids.auto_mode_activated.setVisible(value)
            self.ids.auto_mode_not_activated.setVisible(not value)

        self.parameters.autolock_selection.on_change(autolock_selection_status_changed)

        param2ui(
            self.parameters.autolock_mode_preference, self.ids.autolock_mode_preference
        )

    def kp_changed(self):
        self.parameters.p.value = self.ids.kp.value()
        self.control.write_registers()

    def ki_changed(self):
        self.parameters.i.value = self.ids.ki.value()
        self.control.write_registers()

    def kd_changed(self):
        self.parameters.d.value = self.ids.kd.value()
        self.control.write_registers()

    def lock_mode_changed(self, idx):
        self.parameters.automatic_mode.value = idx == 0

    def autolock_mode_preference_changed(self, idx):
        self.parameters.autolock_mode_preference.value = idx

    def start_manual_lock(self):
        self.parameters.target_slope_rising.value = (
            self.ids.button_slope_rising.isChecked()
        )
        self.parameters.fetch_additional_signals.value = False
        self.parameters.autolock_mode.value = FAST_AUTOLOCK
        self.parameters.autolock_target_position.value = 0
        self.control.write_registers()
        self.control.start_lock()

    def auto_offset_changed(self):
        self.parameters.autolock_determine_offset.value = int(
            self.ids.autoOffsetCheckbox.checkState()
        )

    def pid_on_slow_strength_changed(self):
        self.parameters.pid_on_slow_strength.value = (
            self.ids.pid_on_slow_strength.value()
        )
        self.control.write_registers()

    def start_autolock_selection(self):
        self.parameters.autolock_selection.value = True

    def stop_autolock_selection(self):
        self.parameters.autolock_selection.value = False

    """def watch_lock_threshold_changed(self):
        self.parameters.watch_lock_threshold.value = (
            self.ids.watch_lock_threshold.value() / 100.0
        )"""

    def reset_lock_failed(self):
        self.parameters.autolock_failed.value = False
