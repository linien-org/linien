import os
import sys
import pickle
import _thread
import threading
from time import sleep, time
from rpyc import Service
from rpyc.utils.server import OneShotServer
from PyRedPitaya.board import RedPitaya

sys.path += ['../../']
from linien.config import ACQUISITION_PORT


def shutdown():
    _thread.interrupt_main()
    os._exit(0)


class DataAcquisitionService(Service):
    def __init__(self):
        self.r = RedPitaya()

        self.data = pickle.dumps(None)
        self.data_retrieval_time = None

        super(DataAcquisitionService, self).__init__()

        self.exposed_set_ramp_speed(9)
        self.locked = False
        self.start_time = time()

        self.run()

    def run(self, trigger_delay=16384):
        def run_acquiry_loop():
            while True:
                # copied from https://github.com/RedPitaya/RedPitaya/blob/14cca62dd58f29826ee89f4b28901602f5cdb1d8/api/src/oscilloscope.c#L115
                # check whether scope was triggered
                if (self.r.scope.read(0x1<<2) & 0x4) > 0 and not self.locked:
                    sleep(.05)
                    continue

                data = [
                    [float(i) for i in channel[:]]
                    for channel in
                    (self.r.scope.data_ch1, self.r.scope.data_ch2)
                ]
                self.r.scope.rearm(trigger_source=6)
                self.r.scope.data_decimation = 2 ** self.ramp_speed
                self.r.scope.trigger_delay = trigger_delay - 1
                self.data = pickle.dumps(data)

                if self.data_retrieval_time is None and (time() - self.start_time > 5):
                    # acquisition process is up and running but server did not poll
                    # anything. Maybe it died, so should we
                    print('neverpoll')
                    return shutdown()

                if self.data_retrieval_time is not None:
                    # FIXME: increased this timeout, still necessary?
                    if time() - self.data_retrieval_time > 5:
                        print('nopoll')
                        # the parent process did not poll for more than 2 seconds.
                        # This probably means that it died, so shut down this
                        # child process, too
                        return shutdown()

        self.t = threading.Thread(target=run_acquiry_loop, args=())
        self.t.daemon = True
        self.t.start()

    def exposed_return_data(self):
        self.data_retrieval_time = time()
        return self.data[:]

    def exposed_set_asg_offset(self, idx, value):
        asg = getattr(self.r, ['asga', 'asgb'][idx])
        asg.offset = value

    def exposed_set_ramp_speed(self, speed):
        self.ramp_speed = speed

    def exposed_set_lock_status(self, locked):
        self.locked = locked

if __name__ == '__main__':
    t = OneShotServer(DataAcquisitionService(), port=ACQUISITION_PORT)
    t.start()