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


from typing import Optional

from linien_client.device import Device, add_device, update_device
from linien_gui.config import UI_PATH
from PyQt5 import QtWidgets, uic


class NewDeviceDialog(QtWidgets.QDialog):
    deviceName: QtWidgets.QLineEdit
    host: QtWidgets.QLineEdit
    username: QtWidgets.QLineEdit
    password: QtWidgets.QLineEdit
    port: QtWidgets.QSpinBox
    explainHostLabel: QtWidgets.QLabel

    def __init__(self, device: Optional[Device] = None) -> None:
        super(NewDeviceDialog, self).__init__()
        uic.loadUi(UI_PATH / "new_device_dialog.ui", self)

        if device is None:
            self.is_new_cevice = True
            self.device = Device()  # create a new empty device
        else:
            self.is_new_cevice = False
            self.device = device
            self.explainHostLabel.setVisible(False)

        self.deviceName.setText(self.device.name)
        self.host.setText(self.device.host)
        self.username.setText(self.device.username)
        self.password.setText(self.device.password)
        self.port.setValue(self.device.port)

    def add_new_device(self):
        self.device.name = self.deviceName.text()
        self.device.host = self.host.text()
        self.device.username = self.username.text()
        self.device.password = self.password.text()
        self.device.port = self.port.value()

        if self.is_new_cevice:
            add_device(self.device)
        else:
            update_device(self.device)
