from pyqtgraph.Qt import QtCore


class RemoteParameter:
    """A helper class for `RemoteParameters`, representing a single remote
    parameter."""
    def __init__(self, parent, remote, name):
        self.remote = remote
        self.name = name
        self.parent = parent

    @property
    def value(self):
        return self.parent._get_param(self.name)

    @value.setter
    def value(self, value):
        return self.parent._set_param(self.name, value)

    def change(self, function):
        self.parent.register_listener(self, function)

    def reset(self):
        self.remote.reset()

    @property
    def _start(self):
        return self.remote._start


class RemoteParameters:
    """A class that provides remote access to a `parameters.Parameters` instance.

    It clones the functionality of the remote `Parameters` instance. E.g.:

        r = RemoteParameters(...)
        r.my_param.value = 123

        def on_change(value):
            # do something

        r.my_param.change(on_change)
    """
    def __init__(self, remote, uuid):
        self.remote = remote
        self.uuid = uuid

        for name, param in remote.exposed_get_all_parameters():
            setattr(self, name, RemoteParameter(self, param, name))

        self.call_listeners()

    def __iter__(self):
        for name, param in self.remote.exposed_get_all_parameters():
            yield name, param.value

    def register_listener(self, param, callback):
        self.remote.exposed_register_remote_listener(self.uuid, param.name, callback)

    def call_listeners(self, auto_queue=True):
        # this causes queued remote calls to get processed, see
        # https://rpyc.readthedocs.io/en/latest/tutorial/tut5.html#tut5
        try:
            str(self.remote)
        except:
            print('connection was lost')
            return

        if auto_queue:
            QtCore.QTimer.singleShot(50, self.call_listeners)

    def _get_param(self, param_name):
        return self.remote.exposed_get_param(param_name)

    def _set_param(self, param_name, value):
        return self.remote.exposed_set_param(param_name, value)
