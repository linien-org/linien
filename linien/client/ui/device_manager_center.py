from PyQt5 import QtGui, QtWidgets, QtCore
from linien.client.config import load_device_data, save_device_data
from linien.client.widgets import CustomWidget
from linien.client.ui.new_device_dialog import Ui_NewDeviceDialog
from linien.client.connection import Connection


class DeviceManagerCenter(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.load_device_data(autoload=True)

    def load_device_data(self, autoload=False):
        devices = load_device_data()
        lst = self.ids.deviceList
        lst.clear()

        for device in devices:
            lst.addItem('%s (%s)' % (device['name'], device['host']))

        if autoload and len(devices) == 1:
            self.connect_to_device(devices[0])

    def connect(self):
        devices = load_device_data()

        if not devices:
            return

        self.connect_to_device(devices[self.get_list_index()])

    def connect_to_device(self, device):
        try:
            conn = Connection(device['host'], device['username'], device['password'])
            self.app().connected(conn, conn.parameters, conn.control)
        except:
            pass

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