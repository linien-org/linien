from spectrolock.communication.server import Parameter, BaseParameters


class Parameters(BaseParameters):
    def __init__(self):
        super().__init__()

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
        self.ramp_speed = Parameter(
            min_=10,
            max_=8096,
            start=125
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
