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
from typing import Dict, Tuple

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
from linien_common.communication import RestorableParameterValues
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
    parameter_difference = pyqtSignal(dict)

    def run(self) -> None:
        try:
            self.client = LinienClient(self.device)
            self.client.connect(
                autostart_server=True,
                use_parameter_cache=True,
                call_on_error=self.on_connection_lost,
            )
            self.client_connected.emit(self.client)

            # Check for locally cached settings for this server
            param_diff = self.compare_local_and_remote_parameters()
            if param_diff:
                self.parameter_difference.emit(param_diff)
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

    def on_connection_lost(self) -> None:
        self.connection_lost.emit()

    def compare_local_and_remote_parameters(
        self,
    ) -> Dict[str, Tuple[RestorableParameterValues, RestorableParameterValues]]:
        """Get differences between local and remote parameters."""
        differences = {}
        for local_param_name, local_param_value in self.device.parameters.items():
            if hasattr(self.client.parameters, local_param_name):
                remote_param: RemoteParameter = getattr(
                    self.client.parameters, local_param_name
                )
                if remote_param.value != local_param_value:
                    logger.info(
                        f"Parameter {local_param_name} differs: "
                        f"local={local_param_value}, remote={remote_param.value}"
                    )
                    differences[local_param_name] = (
                        local_param_value,
                        remote_param.value,
                    )
        return differences

    def restore_parameters(
        self,
        differences: Dict[
            str, Tuple[RestorableParameterValues, RestorableParameterValues]
        ],
    ) -> None:
        """Restore the remote parameters with the local ones."""
        logger.info("Restoring parameters...")
        for param_name, (local_value, remote_value) in differences.items():
            remote_param: RemoteParameter = getattr(self.client.parameters, param_name)
            remote_param.value = local_value
        self.client.control.exposed_write_registers()
        logger.info("Parameters restored.")

    def add_callbacks_to_write_parameters_to_disk_on_change(self) -> None:
        """
        Listens for changes of some parameters and permanently saves their values on the
        client's disk. This data can be used to restore the status later, if the client
        tries to connect to the server but it doesn't run anymore.
        """
        for param_name, param in self.client.parameters:
            if param.restorable:

                def on_change(value, parameter_name: str = param_name) -> None:
                    logger.debug(f"Parameter {parameter_name} changed to {value}")
                    if (
                        parameter_name not in self.device.parameters
                        or self.device.parameters[parameter_name] != value
                    ):
                        self.device.parameters[parameter_name] = value
                        update_device(self.device)

                param.add_callback(on_change)
