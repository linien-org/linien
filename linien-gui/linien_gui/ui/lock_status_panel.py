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

from linien_gui.utils import get_linien_app_instance, param2ui
from PyQt5 import QtCore, QtWidgets


class LockStatusPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(LockStatusPanel, self).__init__(*args, **kwargs)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)
        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        self.parent = self.parent()
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
        self.parameters.autolock_preparing.add_callback(self.update_status)
        self.parameters.autolock_failed.add_callback(self.update_status)
        self.parameters.autolock_locked.add_callback(self.update_status)
        self.parameters.autolock_retrying.add_callback(self.update_status)

        param2ui(
            self.parameters.control_signal_history_length,
            self.parent.controlSignalHistoryLengthSpinBox,
        )

    def update_status(self, _) -> None:
        locked = self.parameters.lock.value
        task = self.parameters.task.value
        al_failed = self.parameters.autolock_failed.value
        running = self.parameters.autolock_running.value
        retrying = self.parameters.autolock_retrying.value
        preparing = self.parameters.autolock_preparing.value

        if locked or (task is not None and not al_failed):
            self.show()
        else:
            self.hide()

        if not task:
            running = False

        def set_text(text):
            self.parent.lock_status.setText(text)

        if not running and locked:
            set_text("Locked!")
        if running and not locked and preparing:
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
