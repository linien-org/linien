import random
import string
from socket import gaierror
from time import sleep
from traceback import print_exc

import linien
import rpyc
from linien.client.config import get_saved_parameters, save_parameter
from linien.client.exceptions import (GeneralConnectionErrorException,
                                      InvalidServerVersionException,
                                      ServerNotInstalledException)
from linien.client.remote_parameters import RemoteParameters
from linien.client.utils import run_server
from linien.common import MHz, Vpp
from linien.config import SERVER_PORT
from plumbum import colors


class ClientService(rpyc.Service):
    def __init__(self, uuid):
        super().__init__()

        self.exposed_uuid = uuid


class BaseClient:
    def __init__(self, server, port, use_parameter_cache, call_on_error=None):
        self.use_parameter_cache = use_parameter_cache
        self.uuid = ''.join(random.choice(string.ascii_lowercase) for i in range(10))

        self.client_service = ClientService(self.uuid)

        self.connect(server, port, use_parameter_cache, call_on_error=call_on_error)
        self.connected = True

    def connect(self, server, port, use_parameter_cache, call_on_error=None):
        return self._connect(server, port, use_parameter_cache, call_on_error=call_on_error)

    def _connect(self, server, port, use_parameter_cache, call_on_error=None):
        self.connection = rpyc.connect(server, port, service=self.client_service)

        cls = RemoteParameters
        if call_on_error:
            cls = self.catch_network_errors(cls, call_on_error)

        self.parameters = cls(
            self.connection.root,
            self.uuid,
            use_parameter_cache
        )

    def catch_network_errors(self, cls, call_on_error):
        function_type = type(lambda x: x)
        for attr_name in dir(cls):
            if not attr_name.startswith('__'):
                attr = getattr(cls, attr_name)

                if isinstance(attr, function_type):
                    method = attr
                    def wrapped(*args, method=method, **kwargs):
                        try:
                            return method(*args, **kwargs)
                        except (EOFError,):
                            print(colors.red | 'Connection lost')
                            self.stop()
                            call_on_error()
                            raise

                    setattr(cls, attr_name, wrapped)

        return cls

    def stop(self):
        self.connected = False


class Connection(BaseClient):
    def __init__(self, device, on_connection_lost):
        self.device = device
        self.host = device['host']
        self.user = device.get('username')
        self.password = device.get('password')

        if self.host in ('localhost', '127.0.0.1'):
            # RP is configured such that "localhost" doesn't point to
            # 127.0.0.1 in all cases
            self.host = '127.0.0.1'
        else:
            assert self.user and self.password

        super().__init__(self.host, SERVER_PORT, True, call_on_error=on_connection_lost)

    def connect(self, host, port, use_parameter_cache, call_on_error=None):
        self.connection = None

        i = -1
        server_was_started = False

        while True:
            i += 1

            try:
                print('try to connect to %s:%s' % (host, port))
                self._connect(host, port, use_parameter_cache, call_on_error=call_on_error)
                self.control = self.connection.root
                break
            except gaierror:
                # host not found
                print(colors.red | 'Error: host %s not found' % host)
                break
            except Exception as e:
                if i == 0:
                    print('server is not running. Launching it!')
                    server_was_started = True
                    run_server(host, self.user, self.password)
                    sleep(3)
                else:
                    if i < 20:
                        print('server still not running, waiting (this may take some time)...')
                        sleep(1)
                    else:
                        print_exc()
                        print(colors.red | 'Error: connection to the server could not be established')
                        break

        if self.connection is None:
            raise GeneralConnectionErrorException()

        # now check that the remote version is the same as ours
        remote_version = self.connection.root.exposed_get_server_version()
        client_version = linien.__version__

        if remote_version != client_version:
            raise InvalidServerVersionException(client_version, remote_version)

        print(colors.green | 'connected established!')

        if server_was_started:
            # without this sleep, parameter restoring sometimes crashed the sever
            sleep(1)
            self.restore_parameters()
        self.prepare_parameter_restoring()

    def disconnect(self):
        self.connection.close()

    def prepare_parameter_restoring(self):
        """Listens for changes of some parameters and permanently saves their
        values on the client's disk. This data can be used to restore the status
        later, if the client tries to connect to the server but it doesn't run
        anymore."""
        params = self.parameters.remote.exposed_get_restorable_parameters()

        for param in params:
            def on_change(value, param=param):
                save_parameter(self.device['key'], param, value)

            getattr(self.parameters, param).change(on_change)

    def restore_parameters(self):
        device_key = self.device['key']
        params = get_saved_parameters(device_key)
        print('restoring parameters')

        for k, v in params.items():
            if hasattr(self.parameters, k):
                getattr(self.parameters, k).value = v
            else:
                # this may happen if the settings were written with a different
                # version of linien.
                print('unable to restore parameter %s. Delete the cached value.' % k)
                save_parameter(device_key, k, None, delete=True)

        self.control.write_data()
