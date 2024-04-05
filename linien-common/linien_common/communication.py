# Copyright 2023-2024 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

import hashlib
import logging
import os
import pickle
from socket import socket
from typing import Any, Callable, List, Tuple, Union

from linien_common.influxdb import InfluxDBCredentials
from rpyc.utils.authenticators import AuthenticationError
from typing_extensions import Protocol

from .config import USER_DATA_PATH

HASH_FILE_NAME = "auth_hash.txt"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ParameterValues = Union[int, float, str, bool, Callable, bytes]
RestorableParameterValues = Union[int, float, bool]
PathLike = Union[str, os.PathLike]


class LinienControlService(Protocol):
    def exposed_get_server_version(self) -> str: ...

    def exposed_get_param(self, param_name: str) -> bytes: ...

    def exposed_set_param(self, param_name: str, value: bytes) -> None: ...

    def exposed_reset_param(self, param_name: str) -> None: ...

    def exposed_init_parameter_sync(
        self, uuid: str
    ) -> List[Tuple[str, Any, bool, bool, bool, bool]]: ...

    def exposed_register_remote_listener(self, uuid: str, param_name: str) -> None: ...

    def exposed_register_remote_listeners(
        self, uuid: str, param_names: List[str]
    ) -> None: ...

    def exposed_get_changed_parameters_queue(
        self, uuid: str
    ) -> List[Tuple[str, Any]]: ...

    def exposed_write_registers(self) -> None: ...

    def exposed_start_optimization(self, x0, x1, spectrum) -> None: ...

    def exposed_start_psd_acquisition(self) -> None: ...

    def exposed_start_pid_optimization(self) -> None: ...

    def exposed_start_sweep(self) -> None: ...

    def exposed_start_lock(self) -> None: ...

    def exposed_shutdown(self) -> None: ...

    def exposed_pause_acquisition(self) -> None: ...

    def exposed_continue_acquisition(self) -> None: ...

    def exposed_set_csr_direct(self, key: str, value: int) -> None: ...

    def exposed_set_parameter_log(self, param_name: str, value: bool) -> None: ...

    def exposed_get_parameter_log(self, param_name: str) -> bool: ...

    def exposed_update_influxdb_credentials(
        self, credentials: InfluxDBCredentials
    ) -> Tuple[bool, int, str]: ...

    def exposed_get_influxdb_credentials(self) -> InfluxDBCredentials: ...

    def exposed_start_logging(self, interval: float) -> None: ...

    def exposed_stop_logging(self) -> None: ...

    def exposed_get_logging_status(self) -> bool: ...


def pack(value: ParameterValues) -> Union[bytes, ParameterValues]:
    try:
        return pickle.dumps(value)
    except (TypeError, AttributeError):
        # this happens when un-pickleable objects (e.g. functions) are assigned to a
        # parameter. In this case, we don't pickle it but transfer a netref instead.
        return value


def unpack(value: Union[bytes, ParameterValues]) -> ParameterValues:
    try:
        return pickle.loads(value)  # type: ignore[arg-type]
    except TypeError:
        return value


def hash_username_and_password(username: str, password: str) -> str:
    return hashlib.sha256((username + "/" + password).encode()).hexdigest()


def no_authenticator(sock: socket) -> Tuple[socket, None]:
    """
    Simply reads out the authentication hash so that the connection does not get stuck.
    """
    _ = sock.recv(64)
    return sock, None


def username_and_password_authenticator(sock: socket) -> Tuple[socket, None]:
    """
    Authenticate a client using username and password.
    """
    rpyc_hash = sock.recv(64).decode()
    try:
        with open(str(USER_DATA_PATH / HASH_FILE_NAME), "r") as f:
            file_hash = f.read()
    except FileNotFoundError:
        raise AuthenticationError(
            "No authentication hash found. Start the server  via the client or with the"
            " `--no-auth` flag."
        )
    if file_hash != rpyc_hash:
        raise AuthenticationError("Authentication hashes do not match.")
    return sock, None


def write_hash_to_file(hash: str) -> None:
    with open(str(USER_DATA_PATH / HASH_FILE_NAME), "w") as f:
        f.write(hash)
