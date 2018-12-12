import atexit
import pickle
import threading
import numpy as np
from time import sleep, time
from plumbum import SshMachine
from multiprocessing import Process, Pipe
from rpyc.utils.classic import upload_package
from rpyc.utils.zerodeploy import DeployedServer

from csr import make_filter, PitayaSSH
from server.server import DataAcquisition

# TODO: enum
SHUTDOWN = 0
SET_ASG_OFFSET = 1


class RedPitayaControl:
    def __init__(self, ip, user, password, parameters):
        self.ip = ip
        self.user = user
        self.password = password
        self.parameters = parameters
        self._cached_data = {}

    def connect(self):
        # TODO: Escape
        self.ssh = PitayaSSH(
            ssh_cmd="sshpass -p %s ssh %s@%s" % (self.password, self.user,self.ip)
        )

    def write_data(self):
        params = dict(self.parameters)

        _max = lambda val: val if np.abs(val) <= 8191 else (8191 * val / np.abs(val))
        sweep_min = -1 * _max(params['ramp_amplitude'] * 8191)
        sweep_max = _max(params['ramp_amplitude'] * 8191)

        new = dict(
            # fast_a_x_tap=2,
            # fast_a_demod_delay=params['demodulation_phase'],
            # fast_a_brk=0,
            # fast_a_dx_sel=self.ssh.signal("scopegen_dac_a"),
            # fast_a_dy_sel=self.ssh.signal("zero"),
            # fast_a_y_tap=1,

            # fast_a_sweep_run=0,

            # fast_b_sweep_run=1,
            # fast_b_sweep_step=2 * 125 * params['ramp_amplitude'] * 1024 / params['decimation'],
            # fast_b_sweep_min=sweep_min,
            # fast_b_sweep_max=sweep_max,
            # fast_b_mod_amp=0,
            # fast_b_dy_sel=self.ssh.signal("scopegen_dac_b"),

            # fast_a_mod_amp=params['modulation_amplitude'],
            # #fast_a_mod_amp=0x0,
            # fast_a_mod_freq=params['modulation_frequency'],
            # #fast_a_mod_freq=0,
            # fast_a_y_limit_min=-8192,
            # fast_a_y_limit_max=8191,

            # scopegen_adc_a_sel=self.ssh.signal("fast_a_x"),
            # scopegen_adc_b_sel=self.ssh.signal("fast_b_y"),
            #scopegen_scope_trigger_sel=self.ssh.signal('fast_a_sweep_trigger'),
            #scopegen_scope_trigger_sel=self.ssh.states('pdi0'),
            #scopegen_scope_trigger_sel=self.ssh.signal('zero')

            fast_b_x_tap=2,
            fast_b_demod_delay=params['demodulation_phase'],
            fast_b_brk=0,
            fast_b_dx_sel=self.ssh.signal("scopegen_dac_a"),
            fast_b_y_tap=1,

            fast_b_sweep_run=1,
            fast_b_sweep_step=2 * 125 * params['ramp_amplitude'] * 1024 / params['decimation'],
            fast_b_sweep_min=sweep_min,
            fast_b_sweep_max=sweep_max,
            fast_b_dy_sel=self.ssh.signal("scopegen_dac_b"),

            #fast_b_mod_amp=params['modulation_amplitude'],
            fast_b_mod_freq=params['modulation_frequency'],
            fast_b_mod_amp=0x0,
            #fast_b_mod_freq=0,

            fast_a_brk=0,
            fast_a_mod_amp=params['modulation_amplitude'],
            fast_a_mod_freq=params['modulation_frequency'],
            fast_a_x_tap=2,
            fast_a_demod_delay=params['demodulation_phase'],
            fast_a_sweep_run=0,
            fast_a_dy_sel=self.ssh.signal('zero'),

            fast_b_relock_run=0,
            fast_b_relock_en=self.ssh.states(),
            fast_b_y_hold_en=self.ssh.states(),
            fast_b_y_clear_en=self.ssh.states(),
            fast_b_rx_sel=self.ssh.signal('zero'),

            scopegen_adc_a_sel=self.ssh.signal("fast_b_x"),
            scopegen_adc_b_sel=self.ssh.signal("fast_a_x"),

            gpio_p_oes=0,
            gpio_n_oes=0,

            gpio_p_outs=0,
            gpio_n_outs=0,

            scopegen_external_trigger=2,

            gpio_n_do0_en=self.ssh.signal('zero'),
            gpio_n_do1_en=self.ssh.signal('zero'),

            # asg offset (is not set via ssh but via rpyc)
            asga_offset=0,
            asgb_offset=int(params['center'] * 8191),
        )

        if params['lock']:
            new['fast_b_sweep_run'] = 0
            #new['scopegen_adc_a_sel'] = self.ssh.signal("fast_b_x")

        # filter out values that did not change
        new = dict(
            (k, v)
            for k, v in new.items()
            if (
                (k not in self._cached_data)
                or (self._cached_data.get(k) != v)
            )
        )
        self._cached_data.update(new)

        # set ASG offset
        for idx, asg in enumerate(('asga', 'asgb')):
            try:
                value = new.pop('%s_offset' % asg)
                self.set_asg_offset(idx, value)
            except KeyError:
                pass

        for k, v in new.items():
            self.ssh.set(k, int(v))

        if params['lock']:
            from time import sleep
            self.ssh.set('fast_b_x_clr', 1)
            self.ssh.set('fast_b_y_clr', 1)
            # sync modulation phases
            self.ssh.set('root_sync_phase_en', self.ssh.states('force'))
            self.ssh.set('root_sync_phase_en', self.ssh.states())
            sleep(1)
            print('lock')
            self.ssh.set('fast_b_x_clr', 0)
            self.ssh.set('fast_b_y_clr', 0)
            #self.ssh.set_iir("fast_b_iir_c", *make_filter("P", k=1))
            k = params['k']
            f = params['f']
            self.ssh.set_iir("fast_b_iir_c", *make_filter("PI", k=k, f=f))
        else:
            self.ssh.set_iir("fast_a_iir_a", *make_filter('P', k=1))
            self.ssh.set_iir("fast_a_iir_c", *make_filter("P", k=0))
            self.ssh.set_iir("fast_b_iir_a", *make_filter('P', k=1))
            self.ssh.set_iir("fast_b_iir_c", *make_filter("P", k=0))

        #from time import sleep
        #self.ssh.set('fast_a_mod_freq', int(params['modulation_frequency']/3))
        #sleep(2)
        #self.ssh.set('fast_a_mod_freq', int(params['modulation_frequency']))
        #input('sync?')
        # sync modulation phases
        self.ssh.set('root_sync_phase_en', self.ssh.states('force'))
        self.ssh.set('root_sync_phase_en', self.ssh.states())

    def run_acquiry_loop(self):
        def run_acquiry_loop(conn):
            machine = SshMachine(self.ip, user=self.user, password=self.password)
            deployed_server = DeployedServer(machine, server_class='rpyc.utils.server.OneShotServer')
            classic_conn = deployed_server.classic_connect()

            params = dict(self.parameters)

            upload_package(classic_conn, DataAcquisition)
            acquisition = classic_conn.modules['DataAcquisition.server'].DataAcquisition(
                params['decimation'],
                16384
            )

            """remote_path = classic_conn.modules['os.path']
            bitstream_path = '/redpid.bin'
            if not remote_path.isfile(bitstream_path):
                print('uploading bitstream')

            print('copy')
            remote_shutil = classic_conn.modules['shutil']
            print('got')
            remote_shutil.copyfile(bitstream_path, '/dev/xdevcfg')
            print('copied')
            #remote_subprocess.call('cat %s > /dev/xdevcfg' % bitstream_path, shell=True)
            #print('cat %s > /dev/xdevcfg' % bitstream_path)"""

            conn.send(True)

            while True:
                if conn.poll():
                    data = conn.recv()
                    if data[0] == SHUTDOWN:
                        break
                    elif data[0] == SET_ASG_OFFSET:
                        idx, value = data[1:]
                        print('set2', data[1:])
                        acquisition.set_asg_offset(idx, value)

                data = pickle.loads(acquisition.return_data())

                if data is None:
                    continue

                conn.send([float(i) for i in data])

            deployed_server.close()

        def receive_acquired_data(conn):
            while True:
                self.parameters.to_plot.value = conn.recv()

        self.parent_conn, child_conn = Pipe()
        p = Process(target=run_acquiry_loop, args=(child_conn,))
        p.start()

        # wait until connection is established
        self.parent_conn.recv()
        print('received!')

        t = threading.Thread(target=receive_acquired_data, args=(self.parent_conn,))
        t.daemon = True
        t.start()

        def prepare_exit():
            print('exit')
            self.parent_conn.send((SHUTDOWN,))

        atexit.register(prepare_exit)

    def set_asg_offset(self, idx, offset):
        print('set offset', idx, offset)
        self.parent_conn.send((SET_ASG_OFFSET, idx, offset))