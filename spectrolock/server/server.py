import pickle
import threading
import subprocess
from os import path
from time import sleep, time


class DataAcquisition:
    data = pickle.dumps(None)

    def __init__(self, decimation, trigger_delay):
        from PyRedPitaya.board import RedPitaya
        self.r = RedPitaya()

        self.r.scope.data_decimation = decimation
        self.r.scope.trigger_delay = trigger_delay

        def run_acquiry_loop():
            while True:
                #while True:
                #    #
                #    # sleep(5)
                #    if not r.scope.trigger_bit:
                #        break
                sleep(.4 / 1024 * decimation)
                data = [float(i) for i in self.r.scope.data_ch1[:]]
                self.r.scope.rearm(trigger_source=6)
                self.data = pickle.dumps(data)

        self.t = threading.Thread(target=run_acquiry_loop, args=())
        self.t.daemon = True
        self.t.start()

    def return_data(self):
        return self.data[:]

    def set_asg_offset(self, idx, value):
        asg = getattr(self.r, ['asga', 'asgb'][idx])
        asg.offset = value

if __name__ == '__main__':
    d = DataAcquisition()