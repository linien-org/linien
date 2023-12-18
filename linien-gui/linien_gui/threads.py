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

import logging
import traceback

import rpyc
from linien_client.connection import LinienClient
from linien_client.deploy import install_remote_server
from linien_client.device import Device, update_device
from linien_client.exceptions import (
    GeneralConnectionError,
    InvalidServerVersionException,
    RPYCAuthenticationException,
    ServerNotInstalledException,
)
from linien_client.remote_parameters import RemoteParameter
from PyQt5.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RemoteOutStream(QObject):
    new_item = pyqtSignal(str)

    def write(self, item):
        self.new_item.emit(item)

    def read(self):
        pass

    def flush(self):
        pass


class RemoteServerInstallationThread(QThread):
    def __init__(self, device: Device) -> None:
        """A thread that installs the linien server on a remote machine."""
        super(RemoteServerInstallationThread, self).__init__()
        self.device = device

    out_stream = RemoteOutStream()

    def run(self) -> None:
        install_remote_server(self.device, out_stream=self.out_stream)


class ConnectionThread(QThread):
    def __init__(self, device: Device) -> None:
        super(ConnectionThread, self).__init__()
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
            self.client = LinienClient(self.device)
            self.client.connect(
                autostart_server=True,
                use_parameter_cache=True,
                call_on_error=self.on_connection_lost,
            )
            self.client_connected.emit(self.client)

            # Check for locally cached settings for this server
            parameters_differ = self.restore_parameters(dry_run=True)
            if parameters_differ:
                self.ask_for_parameter_restore.emit()
            else:
                # if parameters don't differ, we can start monitoring remote parameter
                # changes and write them to disk. We don't do this if parameters differ
                # because we don't want to override our local settings with the remote
                # one --> we wait until user has answered whether local parameters or
                # remote ones should be used.
                self.add_callbacks_to_write_parameters_to_disk_on_change()

        except ServerNotInstalledException:
            self.server_not_installed_exception_raised.emit()

        except InvalidServerVersionException as e:
            self.invalid_server_version_exception_raised.emit(
                e.remote_version, e.client_version
            )

        except RPYCAuthenticationException:
            self.authentication_exception_raised.emit()

        except GeneralConnectionError:
            self.general_connection_exception_raised.emit()

        except Exception:
            traceback.print_exc()
            self.other_exception_raised.emit(traceback.format_exc())

    def on_connection_lost(self):
        self.connection_lost.emit()

    def answer_whether_to_restore_parameters(self, should_restore):
        if should_restore:
            self.restore_parameters(dry_run=False)

        self.add_callbacks_to_write_parameters_to_disk_on_change()

    def restore_parameters(self, dry_run: bool = False) -> bool:
        """
        Read settings for a server that were cached locally. Sends them to the server.
        If `dry_run` is...

            * `True`, this function returns a boolean indicating whether the local
              parameters differ from the ones on the server
            * `False`, the local parameters are uploaded to the server
        """
        logger.info("Restoring parameters")
        differences = False
        for param_name, param_value in self.device.parameters.items():
            if hasattr(self.client.parameters, param_name):
                param: RemoteParameter = getattr(self.client.parameters, param_name)
                if param.value != param_value:
                    logger.info(
                        f"Parameter {param_name} differs: "
                        f"local={param_value}, remote={param.value}"
                    )
                    if dry_run:
                        differences = True
                        break
                    else:
                        param.value = param_value
            else:
                # This may happen if the settings were written with a different version
                # of linien.
                logger.warning(
                    f"Unable to restore {param_name}. Delete the cached value."
                )
                del self.device.parameters[param_name]
                update_device(self.device)

        if not dry_run:
            self.client.control.write_registers()

        return differences

    def add_callbacks_to_write_parameters_to_disk_on_change(self) -> None:
        """
        Listens for changes of some parameters and permanently saves their values on the
        client's disk. This data can be used to restore the status later, if the client
        tries to connect to the server but it doesn't run anymore.
        """
        for param_name, param in self.client.parameters:
            if param.restorable:

                def on_change(value, parameter_name: str = param_name) -> None:
                    # FIXME: This is the only part where rpyc is used in linien-gui.
                    # Remove it if possible. rpyc obtain is for ensuring that we don't
                    # try to save a netref here.
                    self.device.parameters[parameter_name] = rpyc.classic.obtain(value)
                    update_device(self.device)

                param.add_callback(on_change)
