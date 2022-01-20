import random
import string

from linien.config import DEFAULT_SERVER_PORT
from linien.gui.config import load_device_data, save_device_data
from linien.gui.widgets import CustomWidget
from PyQt5 import QtWidgets


class NewDeviceDialog(QtWidgets.QDialog, CustomWidget):
    def __init__(self, initial_device=None):
        super().__init__()
        self.load_ui("new_device_dialog.ui")

        if initial_device is not None:
            self.ids.deviceName.setText(initial_device["name"])
            self.ids.host.setText(initial_device["host"])
            self.ids.username.setText(initial_device["username"])
            self.ids.password.setText(initial_device["password"])
            self.ids.port.setValue(initial_device.get("port", DEFAULT_SERVER_PORT))
            self.ids.explain_host.setVisible(False)
            self.key = initial_device["key"]
        else:
            self.key = "".join(random.choice(string.ascii_lowercase) for i in range(10))

    def add_new_device(self):
        device = {
            "key": self.key,
            "name": self.ids.deviceName.text(),
            "host": self.ids.host.text(),
            "username": self.ids.username.text(),
            "password": self.ids.password.text(),
            "port": self.ids.port.value(),
            "params": {},
        }

        old_devices = [
            device for device in load_device_data() if device["key"] != self.key
        ]
        devices = old_devices + [device]
        save_device_data(devices)
