import linien

from time import sleep
from socket import gaierror

from linien.config import SERVER_PORT
from linien.client.utils import run_server
from linien.client.exceptions import GeneralConnectionErrorException, \
    InvalidServerVersionException
from linien.communication.client import BaseClient


class Connection(BaseClient):
    def __init__(self, host, user=None, password=None):
        self.user = user
        self.password = password

        if host in ('localhost', '127.0.0.1'):
            # RP is configured such that "localhost" doesn't point to
            # 127.0.0.1 in all cases
            host = '127.0.0.1'
        else:
            assert user and password

        super().__init__(host, SERVER_PORT, True)

        self.control = self.connection.root

    def connect(self, host, port, use_parameter_cache):
        self.connection = None

        i = -1

        while True:
            i += 1

            try:
                print('try to connect', host, port)
                self._connect(host, port, use_parameter_cache)
                break
            except gaierror:
                # host not found
                print('host not found')
                break
            except Exception as e:
                print('connection error', e)

                if i == 0:
                    print('start server')
                    run_server(host, self.user, self.password)

                    sleep(7)

            sleep(1)

            if i == 10:
                break

        if self.connection is None:
            raise GeneralConnectionErrorException()

        # now check that the remote version is the same as ours
        remote_version = self.connection.root.exposed_get_server_version()
        client_version = linien.__version__

        if remote_version != client_version:
            raise InvalidServerVersionException(client_version, remote_version)

        print('connected', host, port)

    def disconnect(self):
        self.connection.close()