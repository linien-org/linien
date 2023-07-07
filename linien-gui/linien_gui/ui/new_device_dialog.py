# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
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

import random
import string

from linien_common.config import DEFAULT_SERVER_PORT
from linien_gui.config import load_device_data, save_device_data
from linien_gui.widgets import UI_PATH
from PyQt5 import QtWidgets, uic


class NewDeviceDialog(QtWidgets.QDialog):
    deviceName: QtWidgets.QLineEdit
    host: QtWidgets.QLineEdit
    username: QtWidgets.QLineEdit
    password: QtWidgets.QLineEdit
    port: QtWidgets.QSpinBox
    explain_host: QtWidgets.QLabel

    def __init__(self, initial_device=None):
        super(NewDeviceDialog, self).__init__()
        uic.loadUi(UI_PATH / "new_device_dialog.ui", self)

        if initial_device is not None:
            self.deviceName.setText(initial_device["name"])
            self.host.setText(initial_device["host"])
            self.username.setText(initial_device["username"])
            self.password.setText(initial_device["password"])
            self.port.setValue(initial_device.get("port", DEFAULT_SERVER_PORT))
            self.explain_host.setVisible(False)
            self.key = initial_device["key"]
        else:
            self.key = "".join(random.choice(string.ascii_lowercase) for i in range(10))

    def add_new_device(self):
        device = {
            "key": self.key,
            "name": self.deviceName.text(),
            "host": self.host.text(),
            "username": self.username.text(),
            "password": self.password.text(),
            "port": self.port.value(),
            "params": {},
        }

        old_devices = [
            device for device in load_device_data() if device["key"] != self.key
        ]
        devices = old_devices + [device]
        save_device_data(devices)
