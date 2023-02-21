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

import traceback
from queue import Queue

from linien_client.connection import LinienClient
from linien_client.deploy import install_remote_server
from linien_client.exceptions import (
    GeneralConnectionErrorException,
    InvalidServerVersionException,
    RPYCAuthenticationException,
    ServerNotInstalledException,
)
from linien_common.config import DEFAULT_SERVER_PORT
from linien_gui.config import get_saved_parameters, save_parameter
from PyQt5.QtCore import QThread, pyqtSignal


class FileLikeQueue(Queue):
    """
    A queue with the interface of a file-like object used to redirect output stream of
    SSH calls to the GUI.
    """

    def write(self, data):
        self.put(data)

    def read(self):
        return self.get()

    def flush(self):
        pass


class RemoteServerInstallationThread(QThread):
    def __init__(self, device):
        """A thread that installs the linien server on a remote machine."""
        super().__init__()
        self.device = device

    out_stream = FileLikeQueue()

    def run(self):
        install_remote_server(
            host=self.device["host"],
            user=self.device["username"],
            password=self.device["password"],
            out_stream=self.out_stream,
        )


class ConnectionThread(QThread):
    def __init__(self, device):
        super().__init__()
        self.device = device

    client_connected = pyqtSignal(object)
    server_not_installed_exception_raised = pyqtSignal()
    invalid_server_version_exception_raised = pyqtSignal(str, str)
    authentication_exception_raised = pyqtSignal()
    general_connection_exception_raised = pyqtSignal()
    other_exception_raised = pyqtSignal(str)
    connection_lost = pyqtSignal()
    ask_for_parameter_restore = pyqtSignal()

    def run(self):
        try:
            self.client = LinienClient(
                host=self.device["host"],
                user=self.device["username"],
                password=self.device["password"],
                port=self.device.get("port", DEFAULT_SERVER_PORT),
                name=self.device.get("name", ""),
            )
            self.client.connect(
                autostart_server=True,
                use_parameter_cache=True,
                call_on_error=self.on_connection_lost,
            )
            self.client_connected.emit(self.client)

        except ServerNotInstalledException:
            self.server_not_installed_exception_raised.emit()

        except InvalidServerVersionException as e:
            return self.invalid_server_version_exception_raised.emit(
                e.remote_version, e.client_version
            )

        except RPYCAuthenticationException:
            self.authentication_exception_raised.emit()

        except GeneralConnectionErrorException:
            self.general_connection_exception_raised.emit()

        except Exception:
            traceback.print_exc()
            self.other_exception_raised.emit(traceback.format_exc())

        # now, we are connected to the server. Check whether we have cached settings for
        # this server. If yes, check whether they match with what is currentlyrunning.
        # If there is a mismatch, ask the user whether the settings should be restored.

        parameters_differ = self.restore_parameters(dry_run=True)
        if parameters_differ:
            self.ask_for_parameter_restore.emit()
        else:
            # if parameters don't differ, we can start monitoring remote parameter
            # changes and write them to disk. We don't do this if parameters differ
            # because we don't want to override our local settings with the remote one
            # --> we wait until user has answered whether local parameters or remote
            # ones should be used.
            self.continuously_write_parameters_to_disk()

    def on_connection_lost(self):
        self.connection_lost.emit()

    def answer_whether_to_restore_parameters(self, should_restore):
        if should_restore:
            self.restore_parameters(dry_run=False)

        self.continuously_write_parameters_to_disk()

    def restore_parameters(self, dry_run=False):
        """
        Reads settings for a server that were cached locally. Sends them to the server.
        If `dry_run` is...

            * `True`, this function returns a boolean indicating whether the
              local parameters differ from the ones on the server
            * `False`, the local parameters are uploaded to the server
        """
        device_key = self.device["key"]
        params = get_saved_parameters(device_key)
        print("restoring parameters")

        differences = False

        for k, v in params.items():
            if hasattr(self.client.parameters, k):
                param = getattr(self.client.parameters, k)
                if param.value != v:
                    if dry_run:
                        print("parameter", k, "differs")
                        differences = True
                        break
                    else:
                        param.value = v
            else:
                # This may happen if the settings were written with a different version
                # of linien.
                print(f"Unable to restore parameter {k}. Delete the cached value.")
                save_parameter(device_key, k, None, delete=True)

        if not dry_run:
            self.client.control.write_registers()

        return differences

    def continuously_write_parameters_to_disk(self):
        """
        Listens for changes of some parameters and permanently saves their values on the
        client's disk. This data can be used to restore the status later, if the client
        tries to connect to the server but it doesn't run anymore.
        """
        params = self.client.parameters.remote.exposed_get_restorable_parameters()

        for param in params:

            def on_change(value, param=param):
                save_parameter(self.device["key"], param, value)

            getattr(self.client.parameters, param).on_change(on_change)
