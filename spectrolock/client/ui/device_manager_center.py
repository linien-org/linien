from PyQt5 import QtGui, QtWidgets, QtCore
from spectrolock.client.config import load_device_data, save_device_data
from spectrolock.client.widgets import CustomWidget
from spectrolock.client.ui.new_device_dialog import Ui_NewDeviceDialog


class DeviceManagerCenter(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        QtCore.QTimer.singleShot(100, self.load_device_data)

    def connection_established(self):
        pass

    def load_device_data(self):
        devices = load_device_data()
        lst = self.ids.deviceList
        lst.clear()

        for device in devices:
            lst.addItem('%s (%s)' % (device['name'], device['host']))

    def connect(self):
        devices = load_device_data()

        if not devices:
            return

        device = devices[self.get_list_index()]
        self.app().connect(device['host'], device['username'], device['password'])

    def new_device(self):
        self.dialog = QtWidgets.QDialog()
        ui = Ui_NewDeviceDialog()
        ui.setupUi(self.dialog)
        self.dialog.setModal(True)
        self.dialog.show()

        def reload_device_data():
            # not very elegant...
            QtCore.QTimer.singleShot(100, self.load_device_data)

        self.dialog.accepted.connect(reload_device_data)

    def get_list_index(self):
        return self.ids.deviceList.currentIndex().row()

    def remove_device(self):
        devices = load_device_data()

        if not devices:
            return

        devices.pop(self.get_list_index())
        save_device_data(devices)
        self.load_device_data()

    def selected_device_changed(self):
        idx = self.get_list_index()

        disable_buttons = True

        if idx >= 0:
            devices = load_device_data()

            if devices:
                disable_buttons = False

        for btn in [self.ids.connectButton, self.ids.removeButton]:
            btn.setEnabled(not disable_buttons)