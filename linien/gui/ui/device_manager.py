from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal
from threading import Thread
from traceback import print_exc
from paramiko.ssh_exception import AuthenticationException

import linien
from linien.client.config import load_device_data, save_device_data
from linien.gui.widgets import CustomWidget
from linien.client.connection import LinienClient
from linien.gui.dialogs import LoadingDialog, error_dialog, execute_command, \
    question_dialog
from linien.gui.ui.new_device_dialog import NewDeviceDialog
from linien.gui.utils_gui import set_window_icon
from linien.client.exceptions import GeneralConnectionErrorException, \
    InvalidServerVersionException, ServerNotInstalledException


class DeviceManager(QtGui.QMainWindow, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui('device_manager.ui')
        self.setWindowTitle('Linien spectroscopy lock %s' % linien.__version__)
        set_window_icon(self)

    def ready(self):
        self.load_device_data(autoload=True)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.connect()

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
        loading_dialog = LoadingDialog(self, device['host'])
        loading_dialog.show()

        aborted = {}
        def was_aborted(*args):
            aborted['aborted'] = True
        loading_dialog.aborted.connect(was_aborted)

        self.t = ConnectionThread(device)

        def connected(conn):
            loading_dialog.hide()
            if not aborted:
                self.app.connected(conn, conn.parameters, conn.control)
        self.t.connected.connect(connected)

        def server_not_installed():
            client_version = linien.__version__
            loading_dialog.hide()
            if not aborted:
                display_question = """The server is not yet installed on the device. Should it be installed? (Requires internet connection on RedPitaya)"""
                if question_dialog(self, display_question):
                    self.install_linien_server(
                        device, version=client_version if client_version != 'dev' else None
                    )
        self.t.server_not_installed.connect(server_not_installed)

        def invalid_server_version(remote_version, client_version):
            loading_dialog.hide()
            if not aborted:
                if client_version != 'dev':
                    display_question = \
                        "The server version (%s) does not match the client (%s) version." \
                        "Should the corresponding server version be installed?" \
                        % (remote_version, client_version)
                    if question_dialog(self, display_question):
                        self.install_linien_server(device, version=client_version)
                else:
                    display_error = \
                        "A production version is installed on the RedPitaya, " \
                        "but the client uses a development version. Stop the " \
                        "server and uninstall the version on the RedPitaya using\n" \
                        "    linien_stop_server;\n" \
                        "    pip3 uninstall linien-server\n" \
                        "before trying it again."
                    error_dialog(self, display_error)
        self.t.invalid_server_version.connect(invalid_server_version)

        def authentication_exception():
            loading_dialog.hide()
            if not aborted:
                display_error = 'Error at SSH authentication. ' \
                        'Check username and password (by default both are "root") and verify that you ' \
                        'don\'t have any offending SSH keys in your known hosts file.'
                error_dialog(self, display_error)
        self.t.authentication_exception.connect(authentication_exception)

        def general_connection_error():
            loading_dialog.hide()
            if not aborted:
                display_error = "Unable to connect to device."
                error_dialog(self, display_error)
        self.t.general_connection_error.connect(general_connection_error)

        def exception():
            loading_dialog.hide()
            if not aborted:
                display_error = 'Exception occured when connecting to the device.'
                error_dialog(self, display_error)
        self.t.exception.connect(exception)

        def connection_lost():
            error_dialog(self, 'Lost connection to the server!')
            self.app.close()
        self.t.connection_lost.connect(connection_lost)

        self.t.start()

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
                '%s '
                'pip3 install linien-server%s --no-cache-dir; '
                'linien_install_requirements; '
            ) % (stop_server_command, version_string),
            lambda: self.connect_to_device(device)
        )

    def new_device(self):
        self.dialog = NewDeviceDialog()
        self.dialog.setModal(True)
        self.dialog.show()

        def reload_device_data():
            # not very elegant...
            QtCore.QTimer.singleShot(100, self.load_device_data)

        self.dialog.accepted.connect(reload_device_data)

    def edit_device(self):
        devices = load_device_data()

        if not devices:
            return

        device = devices[self.get_list_index()]

        self.dialog = NewDeviceDialog(device)
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

        for btn in [self.ids.connectButton, self.ids.removeButton, self.ids.editButton]:
            btn.setEnabled(not disable_buttons)


class ConnectionThread(QThread):
    connected = pyqtSignal(object)
    server_not_installed = pyqtSignal()
    invalid_server_version = pyqtSignal(str, str)
    authentication_exception = pyqtSignal()
    general_connection_error = pyqtSignal()
    exception = pyqtSignal()
    connection_lost = pyqtSignal()

    def __init__(self, device):
        super().__init__()

        self.device = device

    def run(self):
        try:
            conn = LinienClient(
                self.device,
                autostart_server=True,
                restore_parameters=True,
                use_parameter_cache=True,
                on_connection_lost=self.on_connection_lost
            )
            self.connected.emit(conn)

        except ServerNotInstalledException:
            return self.server_not_installed.emit()

        except InvalidServerVersionException as e:
            return self.invalid_server_version.emit(e.remote_version, e.client_version)

        except AuthenticationException:
            return self.authentication_exception.emit()

        except GeneralConnectionErrorException:
            return self.general_connection_error.emit()

        except Exception as e:
            print_exc()
            return self.exception.emit()

    def on_connection_lost(self):
        self.connection_lost.emit()

