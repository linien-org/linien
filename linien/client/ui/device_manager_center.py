from PyQt5 import QtGui, QtWidgets, QtCore
from traceback import print_exc
from paramiko.ssh_exception import AuthenticationException

from linien.client.config import load_device_data, save_device_data
from linien.client.widgets import CustomWidget
from linien.client.ui.new_device_dialog import Ui_NewDeviceDialog
from linien.client.connection import Connection
from linien.client.exceptions import GeneralConnectionErrorException, \
    ServerNotInstalledException, InvalidServerVersionException
from linien.client.dialogs import loading_dialog, error_dialog, execute_command, \
    question_dialog


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
        self.loading_dialog = loading_dialog(self, device['host'])

        def do():
            connected = False
            display_error = None
            display_question = None

            try:
                conn = Connection(device['host'], device['username'], device['password'])
                connected = True

            except ServerNotInstalledException:
                display_question = """The server is not yet installed on the device. Should it be installed?"""
                question_callback = lambda: \
                    self.install_linien_server(device)

            except InvalidServerVersionException as e:
                display_question = \
                    "The server version (%s) does not match the client (%s) version." \
                    "Should the corresponding server version be installed?" \
                    % (e.remote_version, e.client_version)
                question_callback = lambda v=e.client_version: \
                    self.install_linien_server(device, version=v)

            except AuthenticationException:
                display_error = 'Error at SSH authentication. ' \
                      'Check username and password and verify that you ' \
                      'don\'t have any offending SSH keys in your known ' \
                      'hosts file.'

            except GeneralConnectionErrorException:
                display_error = "Unable to connect to device."

            except Exception as e:
                print_exc()
                display_error = 'Exception occured when connecting to the device.'

            self.loading_dialog.hide()

            if display_error:
                error_dialog(self, display_error)

            elif display_question:
                if question_dialog(self, display_question):
                    question_callback()

            elif connected:
                self.app().connected(conn, conn.parameters, conn.control)

        QtCore.QTimer.singleShot(100, do)

    def install_linien_server(self, device, version=None):
        version_string = ''
        stop_server_command = ''

        if version is not None:
            version_string = '==' + version
            # stop server if another version of linien is installed
            stop_server_command = 'linien_stop_server;'

        self.ssh_command = execute_command(
            self, device['host'], device['username'], device['password'],
            (
                '%s; '
                'pip3 install linien-server%s; '
                'linien_install_requirements; '
            ) % (stop_server_command, version_string),
            lambda: self.connect_to_device(device)
        )

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