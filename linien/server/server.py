import os
import sys
sys.path += ['../../']
import _thread
import pickle

import rpyc
from rpyc.utils.server import ThreadedServer

from registers import Registers
from autolock import Autolock
from parameters import Parameters

from linien.config import SERVER_PORT
from linien.common import update_control_signal_history
from linien.communication.server import BaseService


class RedPitayaControlService(BaseService):
    def __init__(self):
        self._cached_data = {}
        self.exposed_is_locked = None

        super().__init__(Parameters)

        #self.registers = Registers(host='rp-f0685a.local', user='root', password='zeilinger')
        self.registers = Registers()
        self.registers.connect(self, self.parameters)

    def run_acquiry_loop(self):
        def on_change(plot_data):
            self.parameters.to_plot.value = plot_data
            self.parameters.control_signal_history.value = \
                update_control_signal_history(
                    self.parameters.control_signal_history.value,
                    pickle.loads(plot_data),
                    self.exposed_is_locked,
                    self.parameters.control_signal_history_length.value
                )

        self.registers.run_data_acquisition(on_change)

    def exposed_write_data(self):
        self.registers.write_registers()

    def exposed_start_autolock(self, x0, x1, spectrum):
        spectrum = pickle.loads(spectrum)
        start_watching = self.parameters.watch_lock.value

        if not self.parameters.autolock_running.value:
            autolock = Autolock(self, self.parameters)
            self.parameters.task.value = autolock
            autolock.run(x0, x1, spectrum, should_watch_lock=start_watching)

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
        self.registers.acquisition.shutdown()
        _thread.interrupt_main()
        os._exit(0)


class FakeRedPitayaControl(BaseService):
    def __init__(self):
        super().__init__(Parameters)
        self.exposed_is_locked = None

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

    def exposed_shutdown(self):
        _thread.interrupt_main()
        os._exit(0)

    def exposed_start_autolock(self, x0, x1, spectrum):
        print('start autolock', x0, x1)


if __name__ == '__main__':
    control = RedPitayaControlService()
    #control = FakeRedPitayaControl()
    control.run_acquiry_loop()
    control.exposed_write_data()

    t = ThreadedServer(control, port=SERVER_PORT)
    t.start()