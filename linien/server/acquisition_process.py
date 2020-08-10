import os
import sys
import pickle
import _thread
import numpy as np
import threading
from rpyc import Service
from time import sleep, time
from random import random
from rpyc.utils.server import OneShotServer
from PyRedPitaya.board import RedPitaya

sys.path += ['../../']
from csr import make_filter, PitayaLocal
from linien.config import ACQUISITION_PORT
from linien.common import DECIMATION, N_POINTS


# the maximum decimation supported by the FPGA image
MAX_FPGA_DECIMATION = 65536


def shutdown():
    _thread.interrupt_main()
    os._exit(0)


def decimate(array, factor):
    if factor == 1:
        return array

    array = np.array(array)
    array = list(array.reshape(-1, factor).mean(axis=1))
    return array


class DataAcquisitionService(Service):
    def __init__(self):
        self.r = RedPitaya()
        self.csr = PitayaLocal()
        self.csr_queue = []
        self.csr_iir_queue = []

        self.data = pickle.dumps(None)
        self.data_hash = None
        self.skip_next_data = 0
        self.data_uuid = None
        self.additional_decimation = 1

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

                data = self.read_data()

                slow_out = self.csr.get('root_slow_value')
                slow_out = slow_out if slow_out <= 8191 else slow_out - 16384
                data += [slow_out]

                # trigger_source=6 means external trigger positive edge
                self.r.scope.rearm(trigger_source=6)

                if not self.locked:
                    # we use decimation of the FPGA scope for two reasons:
                    # - we want to record at lower scan rates
                    # - we want to record less data points than 16384 data points.
                    #   We could do this by additionally averaging in software, but
                    #   this turned out to be too slow on the RP. Therefore, we
                    #   let the FPGA do this.
                    # With high values of DECIMATION and low scan rates, the required
                    # decimation value exceeds the maximum value supported by the FPGA
                    # image. Therefore, we perform additional software averaging in
                    # these cases. As this happens for slow ramps only, the performance
                    # hit doesn't matter.
                    target_decimation = 2 ** (self.ramp_speed + int(np.log2(DECIMATION)))
                    if target_decimation > MAX_FPGA_DECIMATION:
                        self.additional_decimation = int(target_decimation / MAX_FPGA_DECIMATION)
                        target_decimation = MAX_FPGA_DECIMATION
                    else:
                        self.additional_decimation = 1

                    self.r.scope.data_decimation = target_decimation
                    self.r.scope.trigger_delay = int(trigger_delay / DECIMATION * self.additional_decimation)- 1
                else:
                    self.r.scope.data_decimation = 1
                    self.additional_decimation = 1
                    self.r.scope.trigger_delay = int(trigger_delay / DECIMATION)- 1

                if self.skip_next_data:
                    self.skip_next_data -= 1
                else:
                    self.data = pickle.dumps(data)
                    self.data_hash = random()

        self.t = threading.Thread(target=run_acquiry_loop, args=())
        self.t.daemon = True
        self.t.start()

    def exposed_return_data(self, hash_):
        if hash_ == self.data_hash or self.data_hash is None:
            return False, None, None, None
        else:
            return True, self.data_hash, self.data[:], self.data_uuid

    def exposed_set_ramp_speed(self, speed):
        self.ramp_speed = speed

    def exposed_set_lock_status(self, locked):
        self.locked = locked

    def exposed_set_csr(self, key, value):
        self.csr_queue.append((key, value))

    def exposed_set_iir_csr(self, *args):
        self.csr_iir_queue.append(args)

    def exposed_clear_data_cache(self, uuid):
        self.skip_next_data = 2
        self.data_hash = None
        self.data = None
        self.data_uuid = uuid

    def read_data(self):
        channel_offsets = (0x10000, 0x20000)
        write_pointer = self.r.scope.write_pointer_trigger

        def get_data(offset, addr, data_length):
            max_data_length = 16383
            if data_length + addr > max_data_length:
                to_read_later = data_length + addr - max_data_length
                data_length -= to_read_later
            else:
                to_read_later = 0

            x = self.r.scope.reads(offset+(4*addr), data_length)
            y = x.copy()
            y.dtype = np.int32
            y[y>=2**13] -= 2**14

            if to_read_later > 0:
                y = np.append(y, get_data(offset, 0, to_read_later))

            # IMPORTANT: leave this list comprehension, it is important for
            #            performance when sending the data via rpyc
            return [int(v) for v in y]

        return [
            decimate(
                get_data(channel_offset, write_pointer, N_POINTS * self.additional_decimation),
                self.additional_decimation
            )
            for channel_offset in channel_offsets
        ]


if __name__ == '__main__':
    t = OneShotServer(DataAcquisitionService(), port=ACQUISITION_PORT)
    t.start()