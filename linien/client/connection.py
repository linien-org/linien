from time import sleep
from socket import gaierror

from linien.config import SERVER_PORT
from linien.client.utils import run_server
from linien.communication.client import BaseClient


class ConnectionError(Exception):
    pass


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

        super().__init__(host, SERVER_PORT)

        self.control = self.connection.root

    def connect(self, host, port):
        self.connection = None

        i = -1

        while True:
            i += 1

            try:
                print('try to connect', host, port)
                self._connect(host, port)
                break
            except gaierror:
                # host not found
                print('host not found')
                break
            except Exception as e:
                print('connection error', e)

                if i == 0:
                    print('start server')
                    try:
                        run_server(host, self.user, self.password)
                        sleep(7)
                    except:
                        print('starting server failed')
                        sleep(1)
                        continue

            sleep(1)

            if i == 10:
                break

        if self.connection is None:
            raise ConnectionError()

        print('connected', host, port)

    def disconnect(self):
        self.connection.close()