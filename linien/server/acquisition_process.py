import os
import sys
import pickle
import _thread
import threading
from rpyc import Service
from time import sleep, time
from random import random
from rpyc.utils.server import OneShotServer
from PyRedPitaya.board import RedPitaya

sys.path += ['../../']
from csr import make_filter, PitayaLocal
from linien.config import ACQUISITION_PORT


def shutdown():
    _thread.interrupt_main()
    os._exit(0)


class DataAcquisitionService(Service):
    def __init__(self):
        self.r = RedPitaya()
        self.csr = PitayaLocal()
        self.csr_queue = []
        self.csr_iir_queue = []

        self.data = pickle.dumps(None)
        self.data_hash = None

        super(DataAcquisitionService, self).__init__()

        self.exposed_set_ramp_speed(9)
        self.locked = False

        self.run()

    def run(self, trigger_delay=16384):
        def run_acquiry_loop():
            while True:
                while self.csr_queue:
                    key, value = self.csr_queue.pop(0)
                    self.csr.set(key, value)

                while self.csr_iir_queue:
                    args = self.csr_iir_queue.pop(0)
                    self.csr.set_iir(*args)

                # copied from https://github.com/RedPitaya/RedPitaya/blob/14cca62dd58f29826ee89f4b28901602f5cdb1d8/api/src/oscilloscope.c#L115
                # check whether scope was triggered
                if (self.r.scope.read(0x1<<2) & 0x4) > 0 and not self.locked:
                    sleep(.05)
                    continue

                data = [
                    [int(i) for i in channel[:]]
                    for channel in
                    (self.r.scope.data_ch1, self.r.scope.data_ch2)
                ]

                slow_out = self.csr.get('root_slow_value')
                slow_out = slow_out if slow_out <= 8191 else slow_out - 16384
                data += [slow_out]

                self.r.scope.rearm(trigger_source=6)
                self.r.scope.data_decimation = 2 ** self.ramp_speed
                self.r.scope.trigger_delay = trigger_delay - 1

                self.data = pickle.dumps(data)
                self.data_hash = random()

        self.t = threading.Thread(target=run_acquiry_loop, args=())
        self.t.daemon = True
        self.t.start()

    def exposed_get_data_hash(self):
        return self.data_hash

    def exposed_return_data(self):
        return self.data[:]

    def exposed_set_ramp_speed(self, speed):
        self.ramp_speed = speed

    def exposed_set_lock_status(self, locked):
        self.locked = locked

    def exposed_set_csr(self, key, value):
        self.csr_queue.append((key, value))

    def exposed_set_iir_csr(self, *args):
        self.csr_iir_queue.append(args)



if __name__ == '__main__':
    t = OneShotServer(DataAcquisitionService(), port=ACQUISITION_PORT)
    t.start()