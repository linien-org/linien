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

from linien_gui.utils_gui import param2ui
from linien_gui.widgets import CustomWidget
from PyQt5 import QtWidgets


class LockStatusPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.stop_lock.clicked.connect(self.stop_lock)
        self.ids.control_signal_history_length.setKeyboardTracking(False)
        self.ids.control_signal_history_length.valueChanged.connect(
            self.control_signal_history_length_changed
        )

    def connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        def update_status(_):
            locked = self.parameters.lock.value
            task = self.parameters.task.value
            al_failed = self.parameters.autolock_failed.value
            running = self.parameters.autolock_running.value
            retrying = self.parameters.autolock_retrying.value
            percentage = self.parameters.autolock_percentage.value
            preparing = self.parameters.autolock_preparing.value

            if locked or (task is not None and not al_failed):
                self.show()
            else:
                self.hide()

            if task:
                watching = self.parameters.autolock_watching.value
            else:
                running = False
                watching = False

            def set_text(text):
                self.ids.lock_status.setText(text)

            if not running and locked:
                set_text("Locked!")
            if running and watching:
                set_text("Locked! Watching continuously...")
            if running and not watching and not locked and preparing:
                if not retrying:
                    set_text(
                        "Autolock is running... Analyzing data (%d %%)" % percentage
                    )
                else:
                    set_text("Trying again to lock...")

        for param in (
            self.parameters.lock,
            self.parameters.task,
            self.parameters.autolock_running,
            self.parameters.autolock_preparing,
            self.parameters.autolock_watching,
            self.parameters.autolock_failed,
            self.parameters.autolock_locked,
            self.parameters.autolock_retrying,
            self.parameters.autolock_percentage,
        ):
            param.on_change(update_status)

        param2ui(
            self.parameters.control_signal_history_length,
            self.ids.control_signal_history_length,
        )

    def stop_lock(self):
        self.parameters.fetch_additional_signals.value = True

        if self.parameters.task.value is not None:
            # this may be autolock or psd acquisition
            self.parameters.task.value.stop()
            self.parameters.task.value = None

        self.control.exposed_start_sweep()

    def control_signal_history_length_changed(self):
        self.parameters.control_signal_history_length.value = (
            self.ids.control_signal_history_length.value()
        )
