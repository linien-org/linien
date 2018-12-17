class Parameter:
    def __init__(self, min_=None, max_=None, start=None, wrap=False):
        self.min = min_
        self.max = max_
        self.wrap = wrap
        self._value = start
        self._start = start
        self._listeners = []

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

        for listener in self._listeners:
            listener(value)

    def change(self, function):
        self._listeners.append(function)

        if self._value is not None:
            function(self._value)

    def remove_listener(self, function):
        self._listeners = [
            listener for listener in self._listeners
            if listener != function
        ]

    def reset(self):
        self.value = self._start


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
            max_=0xfff,
            start=0xc00,
            wrap=True
        )
        self.lock = Parameter(start=False)
        self.decimation = Parameter(start=1024)
        self.to_plot = Parameter()

        self.k = Parameter(start=-0.1)
        self.f = Parameter(start=1e-5)
        self.task = Parameter(start=None)

    def __iter__(self):
        for name, element in self.__dict__.items():
            if isinstance(element, Parameter):
                yield name, element.value