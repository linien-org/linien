from rpyc import async_
from linien.common import unpack, pack


class RemoteParameter:
    """A helper class for `RemoteParameters`, representing a single remote
    parameter."""
    def __init__(self, parent, remote, name, use_cache):
        self.remote = remote
        self.name = name
        self.parent = parent

        if use_cache and self.remote.exposed_sync:
            self.change(self._sync_value)

    @property
    def value(self):
        if hasattr(self, '_cached_value'):
            return self._cached_value
        return self.parent._get_param(self.name)

    @value.setter
    def value(self, value):
        return self.parent._set_param(self.name, value)

    def change(self, function):
        self.parent.register_listener(self, function)
        function(self.value)

    def reset(self):
        self.remote.reset()

    @property
    def _start(self):
        return self.remote._start

    def _sync_value(self, value):
        self._cached_value = value


class RemoteParameters:
    """A class that provides remote access to a `parameters.Parameters` instance.

    It clones the functionality of the remote `Parameters` instance. E.g.:

        r = RemoteParameters(...)
        r.my_param.value = 123

        def on_change(value):
            # do something

        r.my_param.change(on_change)
    """
    def __init__(self, remote, uuid, use_cache):
        self.remote = remote
        self.uuid = uuid

        self._listeners = {}

        for name, param in remote.exposed_get_all_parameters():
            setattr(self, name, RemoteParameter(self, param, name, use_cache))

        self.async_listener_queue = None

        self.call_listeners()

    def __iter__(self):
        for name, param in self.remote.exposed_get_all_parameters():
            yield name, getattr(self, name).value

    def register_listener(self, param, callback):
        if param.name not in self._listeners:
            self.remote.exposed_register_remote_listener(self.uuid, param.name)

        self._listeners.setdefault(param.name, [])
        self._listeners[param.name].append(callback)

    def _get_listener_queue_async(self):
        self.async_listener_queue = async_(self.remote.get_listener_queue)(self.uuid)

    def call_listeners(self):
        if self.async_listener_queue is None:
            return self._get_listener_queue_async()

        if self.async_listener_queue.ready:
            queue = unpack(self.async_listener_queue.value)

            self._get_listener_queue_async()

            for param_name, value in queue:
                for listener in self._listeners[param_name]:
                    listener(value)

    def _get_param(self, param_name):
        return unpack(self.remote.exposed_get_param(param_name))

    def _set_param(self, param_name, value):
        return self.remote.exposed_set_param(param_name, pack(value))
