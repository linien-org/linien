import random
import string
from socket import gaierror
from time import sleep
from traceback import print_exc
from typing import Callable

import linien
import rpyc
from linien.client.exceptions import (
    GeneralConnectionErrorException,
    InvalidServerVersionException,
    RPYCAuthenticationException,
    ServerNotRunningException,
)
from linien.client.remote_parameters import RemoteParameters
from linien.client.utils import run_server
from linien.config import DEFAULT_SERVER_PORT
from plumbum import colors

# IMPORTANT: keep this import, because it eases interfacing with the python client
from linien.common import MHz, Vpp, ANALOG_OUT_V, hash_username_and_password

assert MHz
assert Vpp
assert ANALOG_OUT_V


class RPYCClientWithAuthentication(rpyc.Service):
    """An rpyc client that authenticates using a hash.

    This class is run on the client side and exposes the client's unique id
    to the server."""

    def __init__(self, uuid, user, password):
        super().__init__()

        self.exposed_uuid = uuid
        self.auth_hash = hash_username_and_password(user, password).encode()

    def _connect(self, channel, config):
        # send auth hash before rpyc takes over
        channel.stream.sock.send(self.auth_hash)

        return super()._connect(channel, config)


class RawRPYCClient:
    """This class implements the basic functionality for connecting to a Linien
    server using rpyc. See `LinienClient` for higher-level functionality.

    Once connected, communication between server and client mainly takes place
    using the `parameters` attribute."""

    def __init__(
        self,
        server: str,
        port: int,
        user: str,
        password: str,
        use_parameter_cache: bool = False,
        call_on_error: Callable = None,
    ):
        self.use_parameter_cache = use_parameter_cache
        self.uuid = "".join(random.choice(string.ascii_lowercase) for i in range(10))

        # for exposing client's uuid to server
        self.client_service = RPYCClientWithAuthentication(self.uuid, user, password)

        self._connect(
            server,
            port,
            user,
            password,
            use_parameter_cache,
            call_on_error=call_on_error,
        )
        self.connected = True

    def _connect(
        self,
        server: str,
        port: int,
        user: str,
        password: str,
        use_parameter_cache: bool,
        call_on_error: Callable = None,
    ):
        """This method just redirects to `connect_rpyc` and is intended to be
        overridden in inheriting classes."""
        return self._connect_rpyc(
            server,
            port,
            user,
            password,
            use_parameter_cache,
            call_on_error=call_on_error,
        )

    def _connect_rpyc(
        self, server, port, user, password, use_parameter_cache, call_on_error=None
    ):
        """Connect to the server using rpyc and instanciate `RemoteParameters`."""
        self.connection = rpyc.connect(server, port, service=self.client_service)

        cls = RemoteParameters
        if call_on_error:
            cls = self._catch_network_errors(cls, call_on_error)

        self.parameters = cls(self.connection.root, self.uuid, use_parameter_cache)

    def _catch_network_errors(self, cls, call_on_error):
        """This method can be used for patching RemoteParameters such
        that network errors are redirected to `call_on_error`"""
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
                            print(colors.red | "Connection lost")
                            self.connected = False
                            call_on_error()
                            raise

                    setattr(cls, attr_name, wrapped)

        return cls


class LinienClient(RawRPYCClient):
    def __init__(
        self,
        device,
        autostart_server=True,
        use_parameter_cache=False,
        on_connection_lost: Callable = None,
    ):
        self.device = device
        self.host = device["host"]
        user = device.get("username")
        password = device.get("password")

        if self.host in ("localhost", "127.0.0.1"):
            # RP is configured such that "localhost" doesn't point to
            # 127.0.0.1 in all cases
            self.host = "127.0.0.1"
        else:
            assert user and password

        self.autostart_server = autostart_server

        super().__init__(
            self.host,
            device.get("port", DEFAULT_SERVER_PORT),
            user,
            password,
            use_parameter_cache=use_parameter_cache,
            call_on_error=on_connection_lost,
        )

    def _connect(
        self, host, port, user, password, use_parameter_cache, call_on_error=None
    ):
        self.connection = None

        i = -1
        server_was_started = False

        while True:
            i += 1

            try:
                print("try to connect to %s:%s" % (host, port))
                self._connect_rpyc(
                    host,
                    port,
                    user,
                    password,
                    use_parameter_cache,
                    call_on_error=call_on_error,
                )
                self.control = self.connection.root
                break
            except gaierror:
                # host not found
                print(colors.red | "Error: host %s not found" % host)
                break
            except EOFError:
                print("EOFError! Probably authentication failed")
                raise RPYCAuthenticationException()
            except Exception as e:
                if not self.autostart_server:
                    raise ServerNotRunningException()

                if i == 0:
                    print("server is not running. Launching it!")
                    server_was_started = True
                    run_server(host, user, password, port)
                    sleep(3)
                else:
                    if i < 20:
                        print(
                            "server still not running, waiting (this may take some time)..."
                        )
                        sleep(1)
                    else:
                        print_exc()
                        print(
                            colors.red
                            | "Error: connection to the server could not be established"
                        )
                        break

        if self.connection is None:
            raise GeneralConnectionErrorException()

        # now check that the remote version is the same as ours
        remote_version = self.connection.root.exposed_get_server_version()
        client_version = linien.__version__

        if remote_version != client_version:
            raise InvalidServerVersionException(client_version, remote_version)

        print(colors.green | "connected established!")

    def disconnect(self):
        self.connection.close()
        self.connected = False