# Copyright 2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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
import pickle
from socket import socket
from typing import Callable, Tuple, Union

from rpyc.utils.authenticators import AuthenticationError

from .config import USER_DATA_PATH

HASH_FILE_NAME = "auth_hash.txt"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ParameterValues = Union[int, float, str, bool, Callable, bytes]


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
    USER_DATA_PATH.mkdir(parents=True, exist_ok=True)
    with open(str(USER_DATA_PATH / HASH_FILE_NAME), "w") as f:
        f.write(hash)
