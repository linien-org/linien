from PyQt5 import QtGui, QtWidgets, QtCore
from linien.client.config import load_device_data, save_device_data
from linien.client.widgets import CustomWidget
from linien.client.ui.new_device_dialog import Ui_NewDeviceDialog
from linien.client.connection import Connection
from linien.client.exceptions import GeneralConnectionErrorException, \
    ServerNotInstalledException, InvalidServerVersionException


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
        self.loading_dialog = QtWidgets.QMessageBox(self)
        self.loading_dialog.setIcon(QtWidgets.QMessageBox.Information)
        self.loading_dialog.setText('Connecting to %s' % device['host'])
        self.loading_dialog.setWindowTitle('Connecting')
        self.loading_dialog.setModal(True)
        self.loading_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.loading_dialog.setStandardButtons(QtWidgets.QMessageBox.NoButton)
        self.loading_dialog.show()

        def do():
            connected = False
            display_error = None

            try:
                conn = Connection(device['host'], device['username'], device['password'])
                connected = True
            except GeneralConnectionErrorException:
                display_error = "Unable to connect to device"
            except ServerNotInstalledException:
                display_error = """The server is not installed on the device. See XXX."""
            except InvalidServerVersionException as e:
                display_error = """
                The server version (%s) does not match the client (%s) version.
                """ % (e.remote_version, e.client_version)

            self.loading_dialog.hide()

            if display_error:
                self.error_dialog = QtWidgets.QMessageBox(self)
                self.error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
                self.error_dialog.setText(display_error)
                #self.error_dialog.setInformativeText(display_error)
                self.error_dialog.setWindowTitle("Error")
                self.error_dialog.setModal(True)
                self.error_dialog.setWindowModality(QtCore.Qt.WindowModal)
                self.error_dialog.show()

            if connected:
                self.app().connected(conn, conn.parameters, conn.control)

        QtCore.QTimer.singleShot(100, do)

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