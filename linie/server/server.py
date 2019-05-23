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

from linie.config import SERVER_PORT
from linie.communication.server import BaseService


class FakeRedPitayaControl(BaseService):
    def __init__(self):
        super().__init__(Parameters)

    def exposed_write_data(self):
        pass

    def run_acquiry_loop(self):
        import threading
        from time import sleep
        from random import randint

        def run():
            while True:
                self.parameters.to_plot.value = pickle.dumps((
                    [randint(-8192, 8192) for _ in range(16384)],
                    list(_ - 8192 for _ in range(16384))
                ))
                sleep(.1)
        t = threading.Thread(target=run)
        t.daemon = True
        t.start()

    def set_asg_offset(self, idx, offset):
        pass

    def exposed_shutdown(self):
        _thread.interrupt_main()
        os._exit(0)

    def exposed_start_autolock(self, x0, x1):
        print('start autolock', x0, x1)


class RedPitayaControlService(BaseService):
    def __init__(self):
        self._cached_data = {}
        self._is_locked = None

        super().__init__(Parameters)

        pitaya = Pitaya()
        self.pitaya = pitaya
        self.pitaya.connect(self, self.parameters)

    def run_acquiry_loop(self):
        def on_change(plot_data):
            self.parameters.to_plot.value = plot_data

        self.pitaya.listen_for_plot_data_changes(on_change)

    def exposed_write_data(self):
        self.pitaya.write_registers()

    def exposed_set_asg_offset(self, idx, offset):
        self.pitaya.set_asg_offset(idx, offset)

    def exposed_set_ramp_speed(self, speed):
        self.pitaya.set_ramp_speed(speed)

    def exposed_start_autolock(self, x0, x1):
        start_watching = self.parameters.watch_lock.value
        current_task = self.parameters.task.value

        if not current_task or not current_task.running:
            autolock = Autolock(self, self.parameters)
            self.parameters.task.value = autolock
            autolock.run(x0, x1, should_watch_lock=start_watching)

    def exposed_start_ramp(self):
        self.parameters.lock.value = False
        self.exposed_write_data()

    def exposed_start_lock(self):
        self.parameters.lock.value = True
        self.exposed_write_data()

    def exposed_reset(self):
        self.parameters.ramp_amplitude.value = 1
        self.parameters.center.value = 0
        self.exposed_start_ramp()
        self.exposed_write_data()

    def exposed_shutdown(self):
        self.pitaya.shutdown()
        _thread.interrupt_main()
        os._exit(0)


if __name__ == '__main__':
    control = RedPitayaControlService()
    #control = FakeRedPitayaControl()
    control.run_acquiry_loop()
    control.exposed_write_data()

    t = ThreadedServer(control, port=SERVER_PORT)
    t.start()