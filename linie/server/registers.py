import rpyc
import shutil
import atexit
import numpy as np
import threading
from enum import Enum
from time import sleep, time
from multiprocessing import Process, Pipe

from csr import make_filter, PitayaLocal, PitayaSSH
from utils import start_nginx, stop_nginx, start_acquisition_process
from linie.config import ACQUISITION_PORT, DECIMATION


class AcquisitionConnectionError(Exception):
    pass


class AcquisitionProcessSignals(Enum):
    SHUTDOWN = 0
    SET_ASG_OFFSET = 1
    SET_RAMP_SPEED = 2


class Pitaya:
    def __init__(self, host=None, user=None, password=None):
        self.host = host
        self.user = user
        self.password = password

        self.acq_process = None

    def connect(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.use_ssh = self.host is not None and self.host not in ('localhost', '127.0.0.1')

        if self.use_ssh:
            self.pitaya = PitayaSSH(
                ssh_cmd="sshpass -p %s ssh %s@%s" % (self.password, self.user, self.host)
            )
        else:
            self.pitaya = PitayaLocal()

    def write_registers(self):
        params = dict(self.parameters)

        _max = lambda val: val if np.abs(val) <= 8191 else (8191 * val / np.abs(val))
        sweep_min = -1 * _max(params['ramp_amplitude'] * 8191)
        sweep_max = _max(params['ramp_amplitude'] * 8191)

        new = dict(
            # channel B (channel for ramping and PID)
            fast_b_x_tap=2,
            fast_b_demod_delay=params['demodulation_phase'],
            fast_b_brk=0,
            fast_b_dx_sel=self.pitaya.signal("scopegen_dac_a"),
            fast_b_y_tap=4,

            fast_b_sweep_run=1,
            fast_b_sweep_step=2 * int(params['ramp_speed']) * params['ramp_amplitude'] * 1024 / DECIMATION,
            fast_b_sweep_min=sweep_min,
            fast_b_sweep_max=sweep_max,
            fast_b_dy_sel=self.pitaya.signal("scopegen_dac_b"),

            fast_b_mod_freq=params['modulation_frequency'],
            fast_b_mod_amp=0x0,

            fast_b_relock_run=0,
            fast_b_relock_en=self.pitaya.states(),
            fast_b_y_hold_en=self.pitaya.states(),
            fast_b_y_clear_en=self.pitaya.states(),
            fast_b_rx_sel=self.pitaya.signal('zero'),

            # channel A (channel for modulation)
            fast_a_brk=1,
            fast_a_mod_amp=params['modulation_amplitude'],
            fast_a_mod_freq=params['modulation_frequency'],
            fast_a_x_tap=2,
            fast_a_demod_delay=params['demodulation_phase'],
            fast_a_sweep_run=0,
            fast_a_dy_sel=self.pitaya.signal('zero'),

            scopegen_adc_a_sel=self.pitaya.signal("fast_b_x"),
            scopegen_adc_b_sel=self.pitaya.signal("fast_b_y"),
            # trigger on ramp
            scopegen_external_trigger=2,

            gpio_p_oes=0,
            gpio_n_oes=0,

            gpio_p_outs=0,
            gpio_n_outs=0,

            gpio_n_do0_en=self.pitaya.signal('zero'),
            gpio_n_do1_en=self.pitaya.signal('zero'),

            # asg offset (is not set via ssh but via rpyc)
            asga_offset=int(params['offset']),
            asgb_offset=int(params['center'] * 8191),
        )

        lock_changed = params['lock'] != self.control._is_locked
        lock = params['lock']
        self.control._is_locked = lock

        new['fast_b_sweep_run'] = 0 if lock else 1
        #if lock_changed and lock:
            #new['scopegen_adc_a_sel'] = self.pitaya.signal("fast_b_x")

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
                self.control.set_asg_offset(idx, value)
            except KeyError:
                pass

        # pass ramp speed changes to acquisition process
        if 'fast_b_sweep_step' in new:
            self.control.set_ramp_speed(int(params['ramp_speed']))

        for k, v in new.items():
            print('SET', k, v)
            self.pitaya.set(k, int(v))

        if 'fast_b_sweep_step' in new:
            # reset sweep for a short time if the scan range was changed
            # this is needed because otherwise it may take too long before
            # the new scan range is reached --> no scope trigger is sent
            self.pitaya.set('fast_b_sweep_run', 0)
            self.pitaya.set('fast_b_sweep_run', 1)

        kp = params['p']
        ki = params['i']
        kd = params['d']

        if lock_changed:
            if lock:
                # clear
                #self.pitaya.set('fast_b_x_clear_en', self.pitaya.states('force'))
                #self.pitaya.set('fast_b_y_clear_en', self.pitaya.states('force'))

                # sync modulation phases
                self.sync_modulation_phases()

                # set PI parameters
                self.pitaya.set('fast_b_pid_reset', 0)
                self.pitaya.set('fast_b_pid_kp', kp)
                self.pitaya.set('fast_b_pid_ki', ki)
                self.pitaya.set('fast_b_pid_kd', kd)

                # re-enable lock
                #self.pitaya.set('fast_b_y_clear_en', self.pitaya.states())
                #self.pitaya.set('fast_b_x_clear_en', self.pitaya.states())
            else:
                # just enable P with unity gain
                # # FIXME: ZERO!
                unity = 1024
                self.pitaya.set('fast_b_pid_kp', 0)
                self.pitaya.set('fast_b_pid_ki', 0)
                self.pitaya.set('fast_b_pid_kd', 0)
                self.pitaya.set('fast_b_pid_reset', 1)

                self.pitaya.set('fast_a_pid_kp', 0)
                self.pitaya.set('fast_a_pid_ki', 0)
                self.pitaya.set('fast_a_pid_kd', 0)
                self.pitaya.set('fast_a_pid_reset', 1)

                self.pitaya.set_iir("fast_a_iir_a", *make_filter('P', k=1))
                self.pitaya.set_iir("fast_a_iir_c", *make_filter("P", k=0))
                self.pitaya.set_iir("fast_b_iir_a", *make_filter('P', k=1))
                self.pitaya.set_iir("fast_b_iir_c", *make_filter("P", k=0))

        else:
            # hold PID value
            self.pitaya.set('fast_b_y_hold_en', self.pitaya.states('force'))

            if lock:
                # set new PI parameters
                self.pitaya.set('fast_b_pid_kp', kp)
                self.pitaya.set('fast_b_pid_ki', ki)
                self.pitaya.set('fast_b_pid_kd', kd)

            # reset "hold"
            self.pitaya.set('fast_b_y_hold_en', self.pitaya.states())

        self.sync_modulation_phases()

    def sync_modulation_phases(self):
        self.pitaya.set('root_sync_phase_en', self.pitaya.states('force'))
        self.pitaya.set('root_sync_phase_en', self.pitaya.states())

    def listen_for_plot_data_changes(self, on_change):
        def run_acquiry_loop(conn):
            if self.use_ssh:
                pitaya_rpyc = rpyc.connect(self.host, ACQUISITION_PORT)
            else:
                pitaya_rpyc = None

                for i in range(2):
                    try:
                        pitaya_rpyc = rpyc.connect('127.0.0.1', ACQUISITION_PORT)
                    except:
                        if i == 0:
                            stop_nginx()
                            shutil.copyfile('redpid.bin', '/dev/xdevcfg')

                            start_acquisition_process()

                            sleep(2)

            if pitaya_rpyc is None:
                raise AcquisitionConnectionError()

            params = dict(self.parameters)

            sleep_time = float(pitaya_rpyc.root.sleep_time)

            conn.send(True)

            while True:
                t1 = time()

                if conn.poll():
                    data = conn.recv()
                    if data[0] == AcquisitionProcessSignals.SHUTDOWN:
                        break
                    elif data[0] == AcquisitionProcessSignals.SET_ASG_OFFSET:
                        idx, value = data[1:]
                        pitaya_rpyc.root.set_asg_offset(idx, value)
                    elif data[0] == AcquisitionProcessSignals.SET_RAMP_SPEED:
                        speed = data[1]
                        pitaya_rpyc.root.set_ramp_speed(speed)

                data = pitaya_rpyc.root.return_data()

                conn.send(data)

                poll_time = time() - t1
                sleep_time_awaiting = sleep_time - poll_time
                if sleep_time_awaiting > 0:
                    sleep(sleep_time_awaiting)

        def receive_acquired_data(conn):
            while True:
                on_change(conn.recv())

        self.acq_process, child_conn = Pipe()
        p = Process(target=run_acquiry_loop, args=(child_conn,))
        p.start()

        # wait until connection is established
        self.acq_process.recv()

        t = threading.Thread(target=receive_acquired_data, args=(self.acq_process,))
        t.daemon = True
        t.start()

        atexit.register(self.shutdown)

    def set_asg_offset(self, idx, offset):
        self.acq_process.send((AcquisitionProcessSignals.SET_ASG_OFFSET, idx, offset))

    def set_ramp_speed(self, speed):
        self.acq_process.send((AcquisitionProcessSignals.SET_RAMP_SPEED, speed))

    def shutdown(self):
        if self.acq_process:
            self.acq_process.send((AcquisitionProcessSignals.SHUTDOWN,))

        start_nginx()