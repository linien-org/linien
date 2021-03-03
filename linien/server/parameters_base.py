from linien.common import pack


class Parameter:
    """Represents a single parameter and is used by `Parameters`."""

    def __init__(
        self,
        min_=None,
        max_=None,
        start=None,
        wrap=False,
        sync=True,
        collapsed_sync=True,
    ):
        self.min = min_
        self.max = max_
        self.wrap = wrap
        self._value = start
        self._start = start
        self._listeners = set()
        self._collapsed_sync = collapsed_sync
        self.exposed_can_be_cached = sync

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        # check bounds
        if self.min is not None and value < self.min:
            value = self.min if not self.wrap else self.max
        if self.max is not None and value > self.max:
            value = self.max if not self.wrap else self.min

        self._value = value

        # we copy it because a listener could remove a listener --> this would
        # cause an error in this loop
        for listener in self._listeners.copy():
            listener(value)

    def on_change(self, function, call_listener_with_first_value=True):
        self._listeners.add(function)

        if call_listener_with_first_value:
            if self._value is not None:
                function(self._value)

    def remove_listener(self, function):
        if function in self._listeners:
            self._listeners.remove(function)

    def exposed_reset(self):
        self.value = self._start

    def register_remote_listener(self, remote_uuid):
        pass


class BaseParameters:
    """Represents a set of parameters. In an actual program, it should be
    sub-classed like this:

        class MyParameters(BaseParameters):
            def __init__(self):
                self.param1 = Parameter(min_=12, max_=24)

    Parameters can be changed like this:

        p = MyParameters(...)
        p.param1.value = 123

    You can register callback functions like this:

        def on_change(value):
            # do something

        p.param1.on_change(on_change)
    """

    def __init__(self):
        self._remote_listener_queue = {}
        self._remote_listener_callbacks = {}

    def get_all_parameters(self):
        for name, element in self.__dict__.items():
            if isinstance(element, Parameter):
                yield name, element

    def init_parameter_sync(self, uuid):
        """To be called by a remote client: Yields all parameters as well
        as their values and if the parameters are suited to be cached registers
        a listener that pushes changes of these parameters to the client."""
        for name, element in self.get_all_parameters():
            yield name, element, element.value, element.exposed_can_be_cached
            if element.exposed_can_be_cached:
                self.register_remote_listener(uuid, name)

    def register_remote_listener(self, uuid, param_name):
        self._remote_listener_queue.setdefault(uuid, [])
        self._remote_listener_callbacks.setdefault(uuid, [])

        def on_change(value, uuid=uuid, param_name=param_name):
            if uuid in self._remote_listener_queue:
                self._remote_listener_queue[uuid].append((param_name, value))

        param = getattr(self, param_name)
        param.on_change(on_change)

        self._remote_listener_callbacks[uuid].append((param, on_change))

    def unregister_remote_listeners(self, uuid):
        for param, callback in self._remote_listener_callbacks[uuid]:
            param.remove_listener(callback)

        del self._remote_listener_queue[uuid]
        del self._remote_listener_callbacks[uuid]

    def get_listener_queue(self, uuid):
        queue = self._remote_listener_queue.get(uuid, [])
        self._remote_listener_queue[uuid] = []

        # filter out multiple values for collapsible parameters
        already_has_value = []
        for idx in reversed(range(len(queue))):
            param_name, value = queue[idx]
            if self._get_param(param_name)._collapsed_sync:
                if param_name in already_has_value:
                    del queue[idx]
                else:
                    already_has_value.append(param_name)

        return pack(queue)

    def __iter__(self):
        for name, param in self.get_all_parameters():
            yield name, param.value

    def _get_param(self, param_name):
        param = getattr(self, param_name)
        assert isinstance(param, Parameter)
        return param
