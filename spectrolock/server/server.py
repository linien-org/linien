import os
import sys
sys.path += ['../../']
import _thread
import pickle

import rpyc
from rpyc.utils.server import ThreadedServer

from registers import Pitaya
from autolock import Autolock
from parameters import Parameters

from spectrolock.config import SERVER_PORT


class FakeRedPitayaControl(rpyc.Service):
    def __init__(self, ip, user, password, parameters):
        self.parameters = Parameters()

    def write_data(self):
        pass

    def run_acquiry_loop(self):
        from random import randint
        self.parameters.to_plot.value = (
            [randint(-8192, 8192) for _ in range(16384)],
            list(_ - 8192 for _ in range(16384))
        )

    def set_asg_offset(self, idx, offset):
        pass


class RedPitayaControlService(rpyc.Service):
    def __init__(self, pitaya):
        self.parameters = Parameters()
        self._cached_data = {}
        self._is_locked = None

        self.pitaya = pitaya
        self.pitaya.connect(self, self.parameters)

    def write_data(self):
        self.pitaya.write_registers()

    def run_acquiry_loop(self):
        def on_change(plot_data):
            self.parameters.to_plot.value = plot_data

        self.pitaya.listen_for_plot_data_changes(on_change)

    def set_asg_offset(self, idx, offset):
        self.pitaya.set_asg_offset(idx, offset)

    def start_autolock(self, x0, x1):
        autolock = Autolock(self, self.parameters)
        self.parameters.task.value = autolock
        autolock.run(x0, x1)

    def start_ramp(self):
        self.parameters.lock.value = False
        self.write_data()

    def start_lock(self):
        self.parameters.lock.value = True
        self.write_data()

    def reset(self):
        self.parameters.ramp_amplitude.value = 1
        self.parameters.center.value = 0
        self.start_ramp()
        self.write_data()

    def shutdown(self):
        self.pitaya.shutdown()
        _thread.interrupt_main()
        os._exit(0)


if __name__ == '__main__':
    ssh = False

    pitaya = Pitaya()

    control = RedPitayaControlService(pitaya)
    control.run_acquiry_loop()
    control.write_data()

    t = ThreadedServer(control, port=SERVER_PORT, protocol_config={
        'allow_all_attrs': True,
        'allow_setattr': True
    })
    t.start()