class Parameter:
    def __init__(self, min_=None, max_=None, start=None, wrap=False):
        self.min = min_
        self.max = max_
        self.wrap = wrap
        self._value = start
        self._start = start
        self._listeners = set()

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

    def change(self, function):
        self._listeners.add(function)

        if self._value is not None:
            function(self._value)

    def remove_listener(self, function):
        self._listeners.remove(function)

    def reset(self):
        self.value = self._start

    def register_remote_listener(self, remote_uuid):
        pass


class Parameters:
    def __init__(self):
        self.modulation_amplitude = Parameter(
            min_=0,
            max_=0xffff,
            start=4046
        )
        self.modulation_frequency = Parameter(
            min_=0,
            max_=0xffffffff,
            # 0x10000000 ~= 8 MHzs
            start=0x10000000/8*15
        )
        self.center = Parameter(
            min_=-1,
            max_=1,
            start=0
        )
        self.offset = Parameter(
            min_=-8191,
            max_=8191,
            start=0
        )
        self.ramp_amplitude = Parameter(
            min_=0.001,
            max_=1,
            start=1
        )
        self.demodulation_phase = Parameter(
            min_=0,
            max_=0b1111111111111,
            start=0xc00,
            wrap=True
        )
        self.lock = Parameter(start=False)
        self.to_plot = Parameter()

        self.p = Parameter(start=0)
        self.i = Parameter(start=0)
        self.d = Parameter(start=0)
        self.task = Parameter(start=0)
        self.automatic_mode = Parameter(start=True)

        self._remote_listener_queue = {}

    def get_all_parameters(self):
        for name, element in self.__dict__.items():
            if isinstance(element, Parameter):
                yield name, element

    def register_remote_listener(self, uuid, param_name):
        self._remote_listener_queue.setdefault(uuid, set())

        def on_change(value, uuid=uuid, param_name=param_name):
            self._remote_listener_queue[uuid].add(param_name)

        param = getattr(self, param_name)
        param.change(on_change)

    def get_listener_queue(self, uuid):
        queue = self._remote_listener_queue.get(uuid, set())
        self._remote_listener_queue[uuid] = set()
        return queue

    def __iter__(self):
        for name, param in self.get_all_parameters():
            yield name, param.value