# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

import linien_gui
from linien_gui.config import load_device_data, save_device_data
from linien_gui.dialogs import (
    LoadingDialog,
    ask_for_parameter_restore_dialog,
    error_dialog,
    question_dialog,
    show_installation_progress_widget,
)
from linien_gui.threads import ConnectionThread
from linien_gui.ui.new_device_dialog import NewDeviceDialog
from linien_gui.utils import get_linien_app_instance, set_window_icon
from linien_gui.widgets import UI_PATH
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QPushButton


class DeviceManager(QtWidgets.QMainWindow):
    addButton: QPushButton
    connectButton: QPushButton
    editButton: QPushButton
    moveDownButton: QPushButton
    moveUpButton: QPushButton
    removeButton: QPushButton

    def __init__(self, *args, **kwargs):
        super(DeviceManager, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "device_manager.ui", self)
        self.setWindowTitle(f"Linien spectroscopy lock v{linien_gui.__version__}")
        set_window_icon(self)
        self.app = get_linien_app_instance()
        QtCore.QTimer.singleShot(100, lambda: self.load_device_data(autoload=True))

    def keyPressEvent(self, event):
        key = event.key()

        if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.connect()

    def load_device_data(self, autoload=False):
        devices = load_device_data()
        lst = self.deviceList
        lst.clear()

        for device in devices:
            lst.addItem("{} ({})".format(device["name"], device["host"]))

        if autoload and len(devices) == 1:
            self.connect_to_device(devices[0])

    def connect(self):
        devices = load_device_data()

        if not devices:
            return
        else:
            self.connect_to_device(devices[self.get_list_index()])

    def connect_to_device(self, device: dict):
        loading_dialog = LoadingDialog(self, device["host"])
        loading_dialog.show()

        aborted = {}

        self.connection_thread = ConnectionThread(device)

        def was_aborted(*args):
            aborted["aborted"] = True

        loading_dialog.aborted.connect(was_aborted)

        # Define slot functions to be connected ----------------------------------------
        def on_client_connected(client):
            loading_dialog.hide()
            if not aborted:
                self.app.client_connected(client)

        def handle_server_not_installed():
            loading_dialog.hide()
            if not aborted:
                display_question = (
                    "The server is not yet installed on the device. Should it be "
                    "installed? (Requires internet connection on RedPitaya)"
                )
                if question_dialog(self, display_question, "Install server?"):
                    show_installation_progress_widget(
                        parent=self,
                        device=device,
                        callback=lambda: self.connect_to_device(device),
                    )

        def handle_invalid_server_version(
            remote_version: str, client_version: str
        ) -> None:
            loading_dialog.hide()
            if not aborted:
                display_question = (
                    f"Server version ({remote_version}) does not match the client "
                    f"({client_version}) version. Should the corresponding server "
                    f"version be installed?"
                )
                if question_dialog(
                    self, display_question, "Install corresponding version?"
                ):
                    show_installation_progress_widget(
                        parent=self,
                        device=device,
                        callback=lambda: self.connect_to_device(device),
                    )

        def handle_authentication_exception():
            loading_dialog.hide()
            if not aborted:
                display_error = (
                    "Error at authentication.\n"
                    "Check username and password (by default both are 'root')  and "
                    "verify that you don't have any offending SSH keys in your known "
                    "hosts file."
                )
                error_dialog(self, display_error)

        def handle_general_connection_error():
            loading_dialog.hide()
            if not aborted:
                display_error = (
                    "Unable to connect to device. If you are connecting by hostname "
                    "(i.e. `rp-xxxxxx.local`), try using IP address instead."
                )
                error_dialog(self, display_error)

        def handle_other_exception(exception):
            loading_dialog.hide()
            if not aborted:
                display_error = (
                    f"Exception occurred when connecting to the device:\n\n {exception}"
                )
                error_dialog(self, display_error)

        def ask_for_parameter_restore():
            question = (
                "Linien on RedPitaya is running with different parameters than the "
                "ones saved locally on this machine. Do you want to upload the local "
                "parameters or keep the remote ones? Note that remote parameters are "
                "only saved if Linien server was shut down properly, not when "
                "unplugging the power plug. In this case, you should update your local "
                "parameters."
            )
            should_restore = ask_for_parameter_restore_dialog(
                self, question, "Restore parameters?"
            )
            self.connection_thread.answer_whether_to_restore_parameters(should_restore)

        def handle_connection_lost():
            error_dialog(self, "Lost connection to the server!")
            self.app.quit()

        # Connect slots to signals -----------------------------------------------------
        self.connection_thread.client_connected.connect(on_client_connected)

        self.connection_thread.server_not_installed_exception_raised.connect(
            handle_server_not_installed
        )
        self.connection_thread.invalid_server_version_exception_raised.connect(
            handle_invalid_server_version
        )
        self.connection_thread.authentication_exception_raised.connect(
            handle_authentication_exception
        )
        self.connection_thread.general_connection_exception_raised.connect(
            handle_general_connection_error
        )
        self.connection_thread.other_exception_raised.connect(handle_other_exception)
        self.connection_thread.ask_for_parameter_restore.connect(
            ask_for_parameter_restore
        )
        self.connection_thread.connection_lost.connect(handle_connection_lost)

        # Start the worker -------------------------------------------------------------
        self.connection_thread.start()

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

    def move_device_up(self):
        self.move_device(-1)

    def move_device_down(self):
        self.move_device(1)

    def move_device(self, direction):
        devices = load_device_data()

        if not devices:
            return

        current_index = self.get_list_index()
        new_index = current_index + direction

        if new_index < 0 or new_index > len(devices) - 1:
            return

        device = devices.pop(current_index)
        devices = devices[:new_index] + [device] + devices[new_index:]
        save_device_data(devices)
        self.load_device_data()
        self.deviceList.setCurrentRow(new_index)

    def get_list_index(self):
        return self.deviceList.currentIndex().row()

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

        for btn in [
            self.connectButton,
            self.removeButton,
            self.editButton,
            self.moveUpButton,
            self.moveDownButton,
        ]:
            btn.setEnabled(not disable_buttons)
