from linien.config import DEFAULT_COLORS, N_COLORS
from linien.common import Vpp, MHz, pack


class Parameter:
    """Represents a single parameter and is used by `Parameters`."""
    def __init__(self, min_=None, max_=None, start=None, wrap=False, sync=True,
                 collapsed_sync=True):
        self.min = min_
        self.max = max_
        self.wrap = wrap
        self._value = start
        self._start = start
        self._listeners = set()
        self._collapsed_sync = collapsed_sync
        self.exposed_sync = sync

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

        p.param1.change(on_change)
    """
    def __init__(self):
        self._remote_listener_queue = {}
        self._remote_listener_callbacks = {}

    def get_all_parameters(self):
        for name, element in self.__dict__.items():
            if isinstance(element, Parameter):
                yield name, element

    def register_remote_listener(self, uuid, param_name):
        self._remote_listener_queue.setdefault(uuid, [])
        self._remote_listener_callbacks.setdefault(uuid, [])

        def on_change(value, uuid=uuid, param_name=param_name):
            if uuid in self._remote_listener_queue:
                self._remote_listener_queue[uuid].append((param_name, value))

        param = getattr(self, param_name)
        param.change(on_change)

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




class Parameters(BaseParameters):
    def __init__(self):
        super().__init__()

        # parameters whose values are saved on the client and restored if no
        # server is running
        self.restorable_parameters = (
            'modulation_amplitude', 'modulation_frequency', 'ramp_speed',
            'demodulation_phase_a', 'demodulation_multiplier_a',
            'demodulation_phase_b', 'demodulation_multiplier_b',
            'offset_a', 'offset_b', 'invert_a', 'invert_b',
            'filter_1_enabled_a', 'filter_1_enabled_b',
            'filter_1_frequency_a', 'filter_1_frequency_b',
            'filter_1_type_a', 'filter_1_type_b',
            'filter_2_enabled_a', 'filter_2_enabled_b',
            'filter_2_frequency_a', 'filter_2_frequency_b',
            'filter_2_type_a', 'filter_2_type_b',
            'filter_automatic_a', 'filter_automatic_b',
            'p', 'i', 'd', 'watch_lock', 'watch_lock_threshold',
            'dual_channel', 'channel_mixing',
            'pid_on_slow_enabled', 'pid_on_slow_strength',
            'mod_channel', 'control_channel', 'sweep_channel',
            'polarity_fast_out1', 'polarity_fast_out2',
            'polarity_analog_out0', 'autoscale_y', 'y_axis_limits',
            'check_lock', 'analog_out_1', 'analog_out_2', 'analog_out_3',
            'plot_line_width', 'plot_color_0', 'plot_color_1', 'plot_color_2',
            'plot_color_3', 'plot_line_opacity', 'plot_fill_opacity'
        )

        self.modulation_amplitude = Parameter(
            min_=0,
            max_=(1<<14) - 1,
            start=1 * Vpp
        )
        self.modulation_frequency = Parameter(
            min_=0,
            max_=0xffffffff,
            start=15 * MHz
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
            start=8
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
            setattr(self, 'invert_%s' % channel, Parameter(start=False))
            setattr(self, 'filter_automatic_%s' % channel, Parameter(start=True))
            for filter_i in [1, 2]:
                setattr(self, 'filter_%d_enabled_%s' % (filter_i, channel), Parameter(start=False))
                setattr(self, 'filter_%d_type_%s' % (filter_i, channel), Parameter(start=0))
                setattr(self, 'filter_%d_frequency_%s' % (filter_i, channel), Parameter(start=10000))

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
        self.autolock_selection = Parameter(start=False)
        self.autolock_running = Parameter(start=False)
        self.autolock_approaching = Parameter(start=False)
        self.autolock_watching = Parameter(start=False)
        self.autolock_failed = Parameter(start=False)
        self.autolock_locked = Parameter(start=False)
        self.autolock_retrying = Parameter(start=False)
        self.autolock_determine_offset = Parameter(start=True)
        self.autolock_initial_ramp_amplitude = Parameter(start=1)

        self.optimization_selection = Parameter(start=False)
        self.optimization_running = Parameter(start=False)
        self.optimization_approaching = Parameter(start=False)
        self.optimization_improvement = Parameter(start=0)
        self.optimization_mod_freq_enabled = Parameter(start=1)
        self.optimization_mod_freq_min = Parameter(start=0.0)
        self.optimization_mod_freq_max = Parameter(start=10.0)
        self.optimization_mod_amp_enabled = Parameter(start=1)
        self.optimization_mod_amp_min = Parameter(start=0.0)
        self.optimization_mod_amp_max = Parameter(start=2.0)
        self.optimization_optimized_parameters = Parameter(start=(0, 0, 0))
        self.optimization_channel = Parameter(start=0)
        self.optimization_failed = Parameter(start=False)

        self.pause_acquisition = Parameter(start=False)

        self.check_lock = Parameter(start=True)
        self.watch_lock = Parameter(start=True)
        self.watch_lock_threshold = Parameter(start=0.01)

        self.control_signal_history = Parameter(start={
            'times': [],
            'values': []
        }, sync=False)
        # in seconds
        self.control_signal_history_length = Parameter(start=600)

        self.pid_on_slow_enabled = Parameter(start=False)
        self.pid_on_slow_strength = Parameter(start=0)
        self.dual_channel = Parameter(start=False)
        self.channel_mixing = Parameter(start=0)
        # this parameter is not exposed to GUI. It is used by the autolock or
        # normal lock to fetch less data if they are not needed.
        self.fetch_quadratures = Parameter(start=True)

        self.mod_channel = Parameter(start=0, min_=0, max_=1)
        self.control_channel = Parameter(start=1, min_=0, max_=1)
        self.sweep_channel = Parameter(start=1, min_=0, max_=2)

        self.polarity_fast_out1 = Parameter(start=False)
        self.polarity_fast_out2 = Parameter(start=False)
        self.polarity_analog_out0 = Parameter(start=False)

        self.autoscale_y = Parameter(start=True)
        self.y_axis_limits = Parameter(start=1)
        self.plot_line_width = Parameter(start=2, min_=0.1, max_=100)
        self.plot_line_opacity = Parameter(start=230, min_=0, max_=255)
        self.plot_fill_opacity = Parameter(start=70, min_=0, max_=255)

        for color_idx in range(N_COLORS):
            setattr(
                self,
                'plot_color_%d' % color_idx,
                Parameter(start=DEFAULT_COLORS[color_idx])
            )

        self.gpio_p_out = Parameter(start=0, min_=0, max_=0b11111111)
        self.gpio_n_out = Parameter(start=0, min_=0, max_=0b11111111)

        # parameters for ANALOG_OUTs
        for i in range(4):
            if i == 0:
                # ANALOG_OUT0 is used for slow PID
                continue

            setattr(self, 'analog_out_%d' % i, Parameter(start=0, min_=0, max_=(2**15) - 1))