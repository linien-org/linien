import os
import rpyc
import uuid
import pickle
import paramiko

from time import sleep
from socket import gaierror

from kivy.clock import Clock
from spectrolock.config import SERVER_PORT, REMOTE_BASE_PATH


class ConnectionError(Exception):
    pass


class Connection:
    def __init__(self, host, user=None, password=None):
        self.uuid = uuid.uuid4().hex

        if host == 'localhost':
            self.connect_localhost()
        else:
            assert user and password
            self.connect(host, user, password)

        self.parameters = RemoteParameters(
            self.conn.root.parameters,
            self.uuid
        )
        self.control = self.conn.root

    def connect(self, host, user, password):
        self.conn = None

        i = -1

        while True:
            i += 1

            try:
                print('try to connect', host, SERVER_PORT)
                self.conn = rpyc.connect(host, port=SERVER_PORT)
                break
            except gaierror:
                # host not found
                print('host not found')
                sleep(1)
                continue
            except Exception as e:
                print('connection error', e)

                if i == 0:
                    print('start server')
                    try:
                        self.run_server(host, user, password)
                        sleep(5)
                    except:
                        print('starting server failed')
                        sleep(1)
                        continue

            sleep(1)

        if self.conn is None:
            raise ConnectionError()

        print('connected', host, SERVER_PORT)

    def connect_localhost(self):
        try:
            self.conn = rpyc.connect('localhost', port=SERVER_PORT)
        except Exception as e:
            raise ConnectionError from e

    def run_server(self, host, user, password):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, password=password)
        ftp = ssh.open_sftp()

        directory = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '..'
            )
        )

        # upload the code required for running the server
        for dirpath, dirnames, filenames in os.walk(directory):
            if '.' in dirpath or '__' in dirpath:
                continue

            dirpath_rel = dirpath.replace(directory, '').lstrip('/')
            remote_path = os.path.join(REMOTE_BASE_PATH, dirpath_rel)

            try:
                ftp.lstat(remote_path)
            except IOError:
                ftp.mkdir(os.path.join(remote_path.rstrip('/')))

            for filename in filenames:
                local_path = os.path.join(dirpath, filename)
                remote_filepath = os.path.join(remote_path, filename)
                # put file
                ftp.put(local_path, remote_filepath)

        ftp.close()

        # start the server process
        ssh.exec_command('bash %s/server/start_server_in_screen.sh' % REMOTE_BASE_PATH)
        ssh.close()


class RemoteParameter:
    def __init__(self, parent, remote, name):
        self.remote = remote
        self.name = name
        self.parent = parent

    @property
    def value(self):
        return self.remote.value

    @value.setter
    def value(self, value):
        self.remote.value = value

    def change(self, function):
        self.parent.register_listener(self, function)

    def reset(self):
        self.remote.reset()

    @property
    def _start(self):
        return self.remote._start


class RemoteParameters:
    def __init__(self, remote, uuid):
        self.remote = remote
        self.uuid = uuid

        for name, param in remote.get_all_parameters():
            setattr(self, name, RemoteParameter(self, param, name))

        self._listeners = {}

        self.call_listeners()

    def __iter__(self):
        for name, param in self.remote.get_all_parameters():
            yield name, param.value

    def register_listener(self, param, function):
        self.remote.register_remote_listener(self.uuid, param.name)
        self._listeners.setdefault(param.name, [])
        self._listeners[param.name].append(function)

    def call_listeners(self, something=None):
        for param_name in self.remote.get_listener_queue(self.uuid):
            value = getattr(self, param_name).value

            if param_name == 'to_plot':
                if value is None:
                    continue
                value = pickle.loads(value)
                if value is None:
                    continue

            for listener in self._listeners[param_name]:
                listener(value)

        Clock.schedule_once(self.call_listeners, 0.1)