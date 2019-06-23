import uuid
from PyQt5 import QtGui, QtWidgets
from linien.client.config import load_device_data, save_device_data
from linien.client.widgets import CustomWidget


class NewDeviceDialog(QtWidgets.QDialog, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui('new_device_dialog.ui')

    def add_new_device(self):
        device = {
            'key':  uuid.uuid4().hex,
            'name': self.ids.deviceName.text(),
            'host': self.ids.host.text(),
            'username': self.ids.username.text(),
            'password': self.ids.password.text(),
            'params': {}
        }
        devices = load_device_data() + [device]
        save_device_data(devices)