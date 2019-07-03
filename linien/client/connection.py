import linien

from time import sleep
from socket import gaierror
from plumbum import colors
from traceback import print_exc
from PyQt5.QtCore import QThread, pyqtSignal
from paramiko.ssh_exception import AuthenticationException

from linien.config import SERVER_PORT
from linien.client.utils import run_server
from linien.client.config import save_parameter, get_saved_parameters
from linien.client.exceptions import GeneralConnectionErrorException, \
    InvalidServerVersionException, ServerNotInstalledException
from linien.communication.client import BaseClient


MHz = 0x10000000 / 8
Vpp = ((1<<14) - 1) / 4


class ConnectionThread(QThread):
    connected = pyqtSignal(object)
    server_not_installed = pyqtSignal()
    invalid_server_version = pyqtSignal(str, str)
    authentication_exception = pyqtSignal()
    general_connection_error = pyqtSignal()
    exception = pyqtSignal()
    connection_lost = pyqtSignal()

    def __init__(self, device):
        super().__init__()

        self.device = device

    def run(self):
        try:
            conn = Connection(self.device, self.on_connection_lost)
            self.connected.emit(conn)

        except ServerNotInstalledException:
            return self.server_not_installed.emit()

        except InvalidServerVersionException as e:
            return self.invalid_server_version.emit(e.remote_version, e.client_version)

        except AuthenticationException:
            return self.authentication_exception.emit()

        except GeneralConnectionErrorException:
            return self.general_connection_error.emit()

        except Exception as e:
            print_exc()
            return self.exception.emit()

    def on_connection_lost(self):
        self.connection_lost.emit()


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