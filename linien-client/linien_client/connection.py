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

import random
import string
from dataclasses import dataclass
from socket import gaierror
from time import sleep
from traceback import print_exc
from typing import Callable, Optional

import linien_client
import rpyc
from linien_client.deploy import start_remote_server
from linien_client.exceptions import (
    GeneralConnectionErrorException,
    InvalidServerVersionException,
    RPYCAuthenticationException,
    ServerNotRunningException,
)
from linien_client.remote_parameters import RemoteParameters
from linien_common.common import hash_username_and_password
from linien_common.config import DEFAULT_SERVER_PORT


@dataclass
class Device:
    host: str
    user: str
    password: str
    port: int = DEFAULT_SERVER_PORT
    name: str = ""


class RPYCClientWithAuthentication(rpyc.Service):
    """
    An rpyc client that authenticates using a hash.

    This class is run on the client side and exposes the client's unique id to the
    server.
    """

    def __init__(self, uuid: str, user: str, password: str):
        super().__init__()

        self.exposed_uuid = uuid
        self.auth_hash = hash_username_and_password(user, password).encode()

    def _connect(self, channel, config):
        # send auth hash before rpyc takes over
        channel.stream.sock.send(self.auth_hash)

        return super()._connect(channel, config)


class LinienClient:
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = DEFAULT_SERVER_PORT,
        name: str = "",
    ):
        """Connect to a RedPitaya that runs linien server."""
        self.device = Device(host, user, password, port, name)

        if self.device.host in ("localhost", "127.0.0.1"):
            # RP is configured such that "localhost" doesn't point to 127.0.0.1 in all
            # cases
            self.device.host = "127.0.0.1"

        self.uuid = "".join(random.choice(string.ascii_lowercase) for _ in range(10))

        # for exposing client's uuid to server
        self.client_service = RPYCClientWithAuthentication(self.uuid, user, password)

    def connect(
        self,
        autostart_server: bool,
        use_parameter_cache: bool,
        call_on_error: Optional[Callable] = None,
    ) -> None:
        self.connection = None

        i = -1
        while True:
            i += 1
            try:
                print(f"Try to connect to {self.device.host}:{self.device.port}")

                self.connection = rpyc.connect(
                    self.device.host,
                    self.device.port,
                    service=self.client_service,
                    config={"allow_pickle": True},
                )

                cls = RemoteParameters
                if call_on_error:
                    cls = self._catch_network_errors(cls, call_on_error)

                self.parameters = cls(
                    self.connection.root, self.uuid, use_parameter_cache
                )

                self.control = self.connection.root
                break
            except gaierror:
                # host not found
                print(f"Error: host {self.device.host} not found")
                break
            except EOFError:
                print("EOFError! Probably authentication failed")
                raise RPYCAuthenticationException()
            # FIXME: replace with more specific exceptions
            except Exception:
                if not autostart_server:
                    raise ServerNotRunningException()

                if i == 0:
                    print("Server is not running. Launching it!")
                    start_remote_server(
                        self.device.host, self.device.user, self.device.password
                    )
                    sleep(3)
                else:
                    if i < 20:
                        print("Server still not running, waiting (may take some time).")
                        sleep(1)
                    else:
                        print_exc()
                        print(
                            "Error: connection to the server could not be established"
                        )
                        break

        if self.connection is None:
            raise GeneralConnectionErrorException()

        # now check that the remote version is the same as ours
        remote_version = self.connection.root.exposed_get_server_version().split("+")[0]
        local_version = linien_client.__version__.split("+")[0]

        if (remote_version != local_version) and not ("dev" in local_version):
            raise InvalidServerVersionException(local_version, remote_version)

        self.connected = True
        print("Connection established!")

    def disconnect(self) -> None:
        self.connection.close()
        self.connected = False

    def _catch_network_errors(self, cls, call_on_error):
        """
        This method can be used for patching RemoteParameters such that network errors
        are redirected to `call_on_error`
        """
        function_type = type(lambda x: x)

        for attr_name in dir(cls):
            # patch all methods that don't start with __
            if not attr_name.startswith("__"):
                attr = getattr(cls, attr_name)

                if isinstance(attr, function_type):
                    method = attr

                    def wrapped(*args, method=method, **kwargs):
                        try:
                            return method(*args, **kwargs)
                        except (EOFError,):
                            print("Connection lost")
                            self.connected = False
                            call_on_error()
                            raise

                    setattr(cls, attr_name, wrapped)

        return cls
