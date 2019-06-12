from PyQt5 import QtGui
from linien.client.config import load_device_data, save_device_data
from linien.client.widgets import CustomWidget


class NewDeviceDialogCenter(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_new_device(self):
        device = {
            'name': self.ids.deviceName.text(),
            'host': self.ids.host.text(),
            'username': self.ids.username.text(),
            'password': self.ids.password.text()
        }
        devices = load_device_data() + [device]
        save_device_data(devices)