import numpy as np
from time import sleep, time

from csr import make_filter, PitayaLocal, PitayaSSH
from utils import start_nginx, stop_nginx
from linien.config import DEFAULT_RAMP_SPEED
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
        sweep_min = -1 * _max(params['ramp_amplitude'] * 8191)
        sweep_max = _max(params['ramp_amplitude'] * 8191)

        demod_delay = int(
            params['demodulation_phase'] / 360 * (1<<14)
        )
        demod_multiplier = params['demodulation_multiplier']

        new = dict(
            # channel B (channel for ramping and PID)
            fast_b_x_tap=2,
            fast_b_demod_delay=demod_delay,
            fast_b_demod_multiplier=demod_multiplier,
            fast_b_brk=0,
            fast_b_dx_sel=self.rp.signal("scopegen_dac_a"),
            fast_b_y_tap=4,

            fast_b_sweep_run=1,
            fast_b_sweep_step=int(
                DEFAULT_RAMP_SPEED * params['ramp_amplitude']
                / (2 ** params['ramp_speed'])
            ),
            fast_b_sweep_min=sweep_min,
            fast_b_sweep_max=sweep_max,
            fast_b_dy_sel=self.rp.signal("scopegen_dac_b"),

            fast_b_mod_freq=params['modulation_frequency'],
            fast_b_mod_amp=0x0,

            fast_b_relock_run=0,
            fast_b_relock_en=self.rp.states(),
            fast_b_y_hold_en=self.rp.states(),
            fast_b_y_clear_en=self.rp.states(),
            fast_b_rx_sel=self.rp.signal('zero'),

            # channel A (channel for modulation)
            fast_a_brk=1,
            fast_a_mod_amp=params['modulation_amplitude'],
            fast_a_mod_freq=params['modulation_frequency'],
            fast_a_x_tap=2,
            fast_a_demod_delay=demod_delay,
            fast_a_demod_multiplier=demod_multiplier,
            fast_a_sweep_run=0,
            fast_a_pid_kp=0,
            fast_a_pid_ki=0,
            fast_a_pid_kd=0,
            fast_a_dy_sel=self.rp.signal('zero'),

            scopegen_adc_a_sel=self.rp.signal("fast_b_x"),
            scopegen_adc_b_sel=self.rp.signal("fast_b_y"),
            # trigger on ramp
            scopegen_external_trigger=2,

            gpio_p_oes=0,
            gpio_n_oes=0,

            gpio_p_outs=0,
            gpio_n_outs=0,

            gpio_n_do0_en=self.rp.signal('zero'),
            gpio_n_do1_en=self.rp.signal('zero'),

            # asg offset (is not set via ssh but via rpyc)
            asga_offset=int(params['offset']),
            asgb_offset=int(params['center'] * 8191),
        )

        lock_changed = params['lock'] != self.control.exposed_is_locked
        lock = params['lock']
        self.control.exposed_is_locked = lock

        new['fast_b_sweep_run'] = 0 if lock else 1

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

        # set ASG offset
        for idx, asg in enumerate(('asga', 'asgb')):
            try:
                value = new.pop('%s_offset' % asg)
                self.acquisition.set_asg_offset(idx, value)
            except KeyError:
                pass

        # pass ramp speed changes to acquisition process
        if 'fast_b_sweep_step' in new:
            self.acquisition.set_ramp_speed(params['ramp_speed'])

        for k, v in new.items():
            self.rp.set(k, int(v))

        if 'fast_b_sweep_step' in new:
            # reset sweep for a short time if the scan range was changed
            # this is needed because otherwise it may take too long before
            # the new scan range is reached --> no scope trigger is sent
            self.rp.set('fast_b_sweep_run', 0)
            self.rp.set('fast_b_sweep_run', 1)

        kp = params['p']
        ki = params['i']
        kd = params['d']
        slope = params['target_slope_rising']

        if lock_changed:
            if lock:
                # sync modulation phases
                self.sync_modulation_phases()

                # set PI parameters
                self.set_pid(kp, ki, kd, slope, reset=0)
            else:
                self.set_pid(0, 0, 0, slope, reset=1)

                self.rp.set_iir("fast_a_iir_a", *make_filter('P', k=1))
                self.rp.set_iir("fast_a_iir_c", *make_filter("P", k=0))
                self.rp.set_iir("fast_b_iir_a", *make_filter('P', k=1))
                self.rp.set_iir("fast_b_iir_c", *make_filter("P", k=0))

        else:
            # hold PID value
            self.hold_pid(True)

            if lock:
                # set new PI parameters
                self.set_pid(kp, ki, kd, slope)

            # reset "hold"
            self.hold_pid(False)

        self.sync_modulation_phases()

    def sync_modulation_phases(self):
        self.rp.set('root_sync_phase_en', self.rp.states('force'))
        self.rp.set('root_sync_phase_en', self.rp.states())

    def run_data_acquisition(self, on_change):
        self.acquisition = AcquisitionMaster(
            on_change, self.use_ssh, self.host
        )

    def set_pid(self, p, i, d, slope, reset=None):
        sign = -1 if slope else 1
        self.rp.set('fast_b_pid_kp', p * sign)
        self.rp.set('fast_b_pid_ki', i * sign)
        self.rp.set('fast_b_pid_kd', d * sign)

        if reset is not None:
            self.rp.set('fast_b_pid_reset', reset)

    def hold_pid(self, hold):
        self.rp.set(
            'fast_b_y_hold_en',
            self.rp.states('force') if hold else self.rp.states()
        )
