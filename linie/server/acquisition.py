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
from linie.config import ACQUISITION_PORT, DECIMATION, DEFAULT_RAMP_SPEED


class DataAcquisitionService(Service):
    def __init__(self):
        self.r = RedPitaya()

        self.data = pickle.dumps(None)
        self.data_retrieval_time = None

        super(DataAcquisitionService, self).__init__()

        self.set_ramp_speed(DEFAULT_RAMP_SPEED)
        self.run(DECIMATION)

    def run(self, decimation, trigger_delay=16384):
        self.r.scope.data_decimation = decimation
        self.r.scope.trigger_delay = trigger_delay
        self.sleep_time = .4 / 1024 * decimation \
            * (DEFAULT_RAMP_SPEED / self.ramp_speed)

        def run_acquiry_loop():
            while True:
                # FIXME: is sleep really necessary? What happens without it, just comparing the data?
                sleep(self.sleep_time)

                data = [
                    [float(i) for i in channel[:]]
                    for channel in
                    (self.r.scope.data_ch1, self.r.scope.data_ch2)
                ]
                self.r.scope.rearm(trigger_source=6)
                self.data = pickle.dumps(data)

                if self.data_retrieval_time is not None:
                    if time() - self.data_retrieval_time > 2:
                        # the parent process died, shut down this child process, too
                        _thread.interrupt_main()
                        os._exit(0)

        self.t = threading.Thread(target=run_acquiry_loop, args=())
        self.t.daemon = True
        self.t.start()

    def return_data(self):
        self.data_retrieval_time = time()
        return self.data[:]

    def set_asg_offset(self, idx, value):
        asg = getattr(self.r, ['asga', 'asgb'][idx])
        asg.offset = value

    def set_ramp_speed(self, speed):
        self.ramp_speed = speed

if __name__ == '__main__':
    t = OneShotServer(DataAcquisitionService(), port=ACQUISITION_PORT, protocol_config={
        'allow_all_attrs': True,
        'allow_setattr': True
    })
    t.start()