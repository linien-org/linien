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

from typing import Dict, Tuple

import linien_gui
from linien_client.device import Device, delete_device, load_device_list, move_device
from linien_common.communication import RestorableParameterValues
from linien_gui.config import UI_PATH
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
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QListWidget, QPushButton


class DeviceManager(QtWidgets.QMainWindow):
    addButton: QPushButton
    connectButton: QPushButton
    deviceList: QListWidget
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
        QtCore.QTimer.singleShot(100, lambda: self.populate_device_list())

    def keyPressEvent(self, event):
        key = event.key()

        if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.connect()

    def populate_device_list(self):
        self.devices = load_device_list()

        self.deviceList.clear()
        for device in self.devices:
            self.deviceList.addItem(f"{device.name} ({device.host})")

    def connect(self) -> None:
        if not self.devices:
            return
        else:
            self.connect_to_device(self.devices[self.get_list_index()])

    def connect_to_device(self, device: Device):
        loading_dialog = LoadingDialog(self, device.host)
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

        def ask_for_parameter_restore(
            parameter_difference: Dict[
                str, Tuple[RestorableParameterValues, RestorableParameterValues]
            ]
        ) -> None:
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
            if should_restore:
                self.connection_thread.restore_parameters(parameter_difference)
            self.connection_thread.add_callbacks_to_write_parameters_to_disk_on_change()

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
        self.connection_thread.parameter_difference.connect(ask_for_parameter_restore)
        self.connection_thread.connection_lost.connect(handle_connection_lost)

        # Start the worker -------------------------------------------------------------
        self.connection_thread.start()

    def get_list_index(self):
        """Get the currently selected device index from the device list."""
        return self.deviceList.currentIndex().row()

    def reload_device_data(self) -> None:
        # not very elegant...
        QtCore.QTimer.singleShot(100, self.populate_device_list)

    def new_device(self) -> None:
        """Open the dialog to create a new device."""
        self.dialog = NewDeviceDialog()
        self.dialog.setModal(True)
        self.dialog.show()
        self.dialog.accepted.connect(self.reload_device_data)

    def edit_device(self) -> None:
        """Open the dialog to edit the currently selected device."""
        device = self.devices[self.get_list_index()]

        self.dialog = NewDeviceDialog(device)
        self.dialog.setModal(True)
        self.dialog.show()
        self.dialog.accepted.connect(self.reload_device_data)

    def move_device_up(self) -> None:
        """Move the currently selected device up in the list."""
        self.move_device_in_list(-1)

    def move_device_down(self) -> None:
        """Move the currently selected device down in the list."""
        self.move_device_in_list(1)

    def move_device_in_list(self, direction: int) -> None:
        """Move the currently selected device in the list by the given direction."""
        selected_index = self.get_list_index()
        selected_device = self.devices[selected_index]
        move_device(selected_device, direction)
        self.populate_device_list()
        self.deviceList.setCurrentRow(selected_index + direction)

    def remove_device(self) -> None:
        """
        Remove the currently selected device from the list and save new list to disk.
        """
        selected_device = self.devices[self.get_list_index()]
        delete_device(selected_device)
        self.populate_device_list()

    def selected_device_changed(self) -> None:
        disable_buttons = True

        if self.get_list_index() >= 0:
            if self.devices:
                disable_buttons = False

        for button in [
            self.connectButton,
            self.removeButton,
            self.editButton,
            self.moveUpButton,
            self.moveDownButton,
        ]:
            button.setEnabled(not disable_buttons)
