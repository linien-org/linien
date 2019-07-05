from linien.communication.server import Parameter, BaseParameters


class Parameters(BaseParameters):
    def __init__(self):
        super().__init__()

        # parameters whose values are saved on the client and restored if no
        # server is running
        self.restorable_parameters = (
            'modulation_amplitude', 'modulation_frequency', 'ramp_speed',
            'demodulation_phase_a', 'demodulation_multiplier_a',
            'demodulation_phase_b', 'demodulation_multiplier_b',
            'offset_a', 'offset_b',
            'filter_1_enabled_a', 'filter_1_enabled_b',
            'filter_1_frequency_a', 'filter_1_frequency_b',
            'filter_1_type_a', 'filter_1_type_b',
            'filter_2_enabled_a', 'filter_2_enabled_b',
            'filter_2_frequency_a', 'filter_2_frequency_b',
            'filter_2_type_a', 'filter_2_type_b',
            'p', 'i', 'd', 'watch_lock', 'ramp_on_slow', 'dual_channel',
            'channel_mixing', 'enable_slow_out', 'slow_polarity_inverted',
            'pid_on_slow_enabled', 'pid_on_slow_strength'
        )

        self.modulation_amplitude = Parameter(
            min_=0,
            max_=(1<<14) - 1,
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

        self.ramp_amplitude = Parameter(
            min_=0.001,
            max_=1,
            start=1
        )
        self.ramp_speed = Parameter(
            min_=0,
            max_=16,
            start=9
        )

        for channel in ('a', 'b'):
            setattr(self, 'demodulation_phase_%s' % channel, Parameter(
                min_=0,
                max_=360,
                start=0x0,
                wrap=True
            ))
            setattr(self, 'demodulation_multiplier_%s' % channel, Parameter(
                min_=0,
                max_=15,
                start=1
            ))
            setattr(self, 'offset_%s' % channel, Parameter(
                min_=-8191,
                max_=8191,
                start=0
            ))
            for filter_i in [1, 2]:
                setattr(self, 'filter_%d_enabled_%s' % (filter_i, channel), Parameter(start=False))
                setattr(self, 'filter_%d_type_%s' % (filter_i, channel), Parameter(start=0))
                setattr(self, 'filter_%d_frequency_%s' % (filter_i, channel), Parameter(start=0))

        self.combined_offset = Parameter(
            min_=-8191,
            max_=8191,
            start=0
        )

        self.lock = Parameter(start=False)
        self.to_plot = Parameter()

        self.p = Parameter(start=50)
        self.i = Parameter(start=5)
        self.d = Parameter(start=0)
        self.task = Parameter(start=None, sync=False)
        self.automatic_mode = Parameter(start=True)
        self.target_slope_rising = Parameter(start=True)
        self.autolock_running = Parameter(start=False)
        self.autolock_approaching = Parameter(start=False)
        self.autolock_watching = Parameter(start=False)
        self.autolock_failed = Parameter(start=False)
        self.autolock_locked = Parameter(start=False)
        self.autolock_determine_offset = Parameter(start=True)
        self.autolock_initial_ramp_amplitude = Parameter(start=1)
        self.pause_acquisition = Parameter(start=False)

        self.watch_lock = Parameter(start=True)
        self.control_signal_history = Parameter(start={
            'times': [],
            'values': []
        }, sync=False)
        # in seconds
        self.control_signal_history_length = Parameter(start=600)

        self.enable_slow_out = Parameter(start=False)
        self.ramp_on_slow = Parameter(start=False)
        self.slow_polarity_inverted = Parameter(start=False)
        self.pid_on_slow_enabled = Parameter(start=False)
        self.pid_on_slow_strength = Parameter(start=0)
        self.dual_channel = Parameter(start=False)
        self.channel_mixing = Parameter(start=0)
