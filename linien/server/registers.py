import numpy as np
from time import sleep, time

from csr import make_filter, PitayaLocal, PitayaSSH
from utils import start_nginx, stop_nginx, twos_complement
from linien.config import DEFAULT_RAMP_SPEED
from linien.common import convert_channel_mixing_value, \
    LOW_PASS_FILTER, HIGH_PASS_FILTER
from linien.server.acquisition import AcquisitionMaster


class Registers:
    def __init__(self, host=None, user=None, password=None):
        self.host = host
        self.user = user
        self.password = password
        self.acquisition = None

    def connect(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.use_ssh = self.host is not None and self.host not in ('localhost', '127.0.0.1')

        if self.use_ssh:
            self.rp = PitayaSSH(
                ssh_cmd="sshpass -p %s ssh %s@%s" % (self.password, self.user, self.host)
            )
        else:
            self.rp = PitayaLocal()

        def lock_status_changed(v):
            if self.acquisition is not None:
                self.acquisition.lock_status_changed(v)

        self.parameters.lock.change(lock_status_changed)

    def write_registers(self):
        params = dict(self.parameters)

        _max = lambda val: val if np.abs(val) <= 8191 else (8191 * val / np.abs(val))
        phase_to_delay = lambda phase: int(phase / 360 * (1<<14))

        if not params['dual_channel']:
            factor_a = 256
            factor_b = 0
        else:
            value = params['channel_mixing']
            factor_a, factor_b = convert_channel_mixing_value(value)

        lock = params['lock']
        lock_changed = lock != self.control.exposed_is_locked
        self.control.exposed_is_locked = lock

        new = dict(
            root_sweep_run=0 if lock else 1,
            root_sweep_step=int(
                DEFAULT_RAMP_SPEED * params['ramp_amplitude']
                / (2 ** params['ramp_speed'])
            ),
            root_sweep_min=-1 * _max(params['ramp_amplitude'] * 8191),
            root_sweep_max=_max(params['ramp_amplitude'] * 8191),
            root_ramp_on_slow=params['enable_slow_out'] and params['ramp_on_slow'],

            root_mod_freq=params['modulation_frequency'],
            root_mod_amp=params['modulation_amplitude'],

            root_chain_a_factor=factor_a,
            root_chain_b_factor=factor_b,
            root_chain_a_offset=twos_complement(int(params['offset_a']), 14),
            root_chain_b_offset=twos_complement(int(params['offset_b']), 14),
            root_out_offset=int(params['center'] * 8191),
            root_combined_offset=twos_complement(params['combined_offset'], 14),

            slow_pid_reset=not (params['enable_slow_out'] and params['pid_on_slow_enabled']),

            # channel A
            fast_a_x_tap=2,
            fast_a_demod_delay=phase_to_delay(params['demodulation_phase_a']),
            fast_a_demod_multiplier=params['demodulation_multiplier_a'],
            fast_a_brk=0,
            fast_a_dx_sel=self.rp.signal('zero'),
            fast_a_y_tap=2,
            fast_a_dy_sel=self.rp.signal('zero'),

            fast_a_y_hold_en=self.rp.states(),
            fast_a_y_clear_en=self.rp.states(),
            fast_a_rx_sel=self.rp.signal('zero'),

            # channel B
            fast_b_x_tap=2,
            fast_b_demod_delay=phase_to_delay(params['demodulation_phase_b']),
            fast_b_demod_multiplier=params['demodulation_multiplier_b'],
            fast_b_brk=0,
            fast_b_dx_sel=self.rp.signal('zero'),
            fast_b_y_tap=1,
            fast_b_dy_sel=self.rp.signal('zero'),

            fast_b_y_hold_en=self.rp.states(),
            fast_b_y_clear_en=self.rp.states(),
            fast_b_rx_sel=self.rp.signal('zero'),

            # trigger on ramp
            scopegen_external_trigger=1,

            gpio_p_oes=0,
            gpio_n_oes=0b1,

            gpio_p_outs=0,
            gpio_n_outs=0b1 if params['lock'] else 0b0,

            gpio_n_do0_en=self.rp.signal('zero'),
            gpio_n_do1_en=self.rp.signal('zero'),
        )

        if lock:
            # display combined error signal and control signal
            new.update({
                'scopegen_adc_a_sel': self.rp.signal('root_combined_error_signal'),
                'scopegen_adc_b_sel': self.rp.signal('root_control_signal')
            })
        else:
            # display both demodulated error signals
            new.update({
                'scopegen_adc_a_sel': self.rp.signal("fast_a_y"),
                'scopegen_adc_b_sel': self.rp.signal("fast_b_y")
            })


        # filter out values that did not change
        new = dict(
            (k, v)
            for k, v in new.items()
            if (
                (k not in self.control._cached_data)
                or (self.control._cached_data.get(k) != v)
            )
        )
        self.control._cached_data.update(new)

        # pass ramp speed changes to acquisition process
        if 'root_sweep_step' in new:
            self.acquisition.set_ramp_speed(params['ramp_speed'])

        for k, v in new.items():
            self.rp.set(k, int(v))

        if 'root_sweep_step' in new:
            # reset sweep for a short time if the scan range was changed
            # this is needed because otherwise it may take too long before
            # the new scan range is reached --> no scope trigger is sent
            self.rp.set('root_sweep_run', 0)
            self.rp.set('root_sweep_run', 1)

        kp = params['p']
        ki = params['i']
        kd = params['d']
        slope = params['target_slope_rising']
        invert = params['ramp_on_slow'] and params['slow_polarity_inverted']
        if invert:
            slope = not slope
        slow_strength = params['pid_on_slow_strength']
        slow_slope = slope
        if params['slow_polarity_inverted']:
            slow_slope = not slow_slope

        for chain in ('a', 'b'):
            for iir_idx in range(2):
                iir_name = 'fast_%s_iir_%s' % (chain, ('c', 'd')[iir_idx])

                filter_enabled = params['filter_%d_enabled_%s' % (iir_idx + 1, chain)]
                filter_type = params['filter_%d_type_%s' % (iir_idx + 1, chain)]
                filter_frequency = params['filter_%d_frequency_%s' % (iir_idx + 1, chain)]
                base_freq = 125e6

                if not filter_enabled:
                    self.rp.set_iir(iir_name, *make_filter('P', k=1))
                else:
                    if filter_type == LOW_PASS_FILTER:
                        self.rp.set_iir(iir_name, *make_filter(
                            'LP', f=filter_frequency / base_freq, k=1
                        ))
                    elif filter_type == HIGH_PASS_FILTER:
                        self.rp.set_iir(iir_name, *make_filter(
                            'HP', f=filter_frequency / base_freq, k=1
                        ))
                    else:
                        raise Exception('unknown filter %s for %s' (filter_type, iir_name))

        if lock_changed:
            if lock:
                # set PI parameters
                self.set_pid(kp, ki, kd, slope, reset=0)
                self.set_slow_pid(slow_strength, slow_slope, reset=0)
            else:
                self.set_pid(0, 0, 0, slope, reset=1)
                self.set_slow_pid(0, slow_slope, reset=1)

                self.rp.set_iir("fast_a_iir_a", *make_filter('P', k=1))
                self.rp.set_iir("fast_b_iir_a", *make_filter('P', k=1))

        else:
            if lock:
                # hold PID value
                self.hold_pid(True)

                # set new PI parameters
                self.set_pid(kp, ki, kd, slope)
                self.set_slow_pid(slow_strength, slow_slope)

                # reset "hold"
                self.hold_pid(False)

    def run_data_acquisition(self, on_change):
        self.acquisition = AcquisitionMaster(
            on_change, self.use_ssh, self.host
        )

    def set_pid(self, p, i, d, slope, reset=None):
        sign = -1 if slope else 1
        self.rp.set('root_pid_kp', p * sign)
        self.rp.set('root_pid_ki', i * sign)
        self.rp.set('root_pid_kd', d * sign)

        if reset is not None:
            self.rp.set('root_pid_reset', reset)

    def set_slow_pid(self, strength, slope, reset=None):
        sign = -1 if slope else 1
        self.rp.set('slow_pid_ki', strength * sign)

        if reset is not None:
            self.rp.set('slow_pid_reset', reset)

    def hold_pid(self, hold):
        # FIXME: root?
        self.rp.set(
            'fast_b_y_hold_en',
            self.rp.states('force') if hold else self.rp.states()
        )
        self.rp.set(
            'fast_a_y_hold_en',
            self.rp.states('force') if hold else self.rp.states()
        )

    def get_slow_value(self):
        v = self.rp.get('slow_value')
        return v if (v <= 8191) else (v - 16384)