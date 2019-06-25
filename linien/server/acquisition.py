import sys
sys.path += ['../../']
import rpyc
import atexit
import threading

from enum import Enum
from time import sleep
from multiprocessing import Process, Pipe

from linien.config import ACQUISITION_PORT
from linien.server.utils import stop_nginx, start_nginx, flash_fpga

class AcquisitionConnectionError(Exception):
    pass


class AcquisitionProcessSignals(Enum):
    SHUTDOWN = 0
    SET_RAMP_SPEED = 2
    SET_LOCK_STATUS = 3


class AcquisitionMaster:
    def __init__(self, on_acquisition, use_ssh, host):
        def receive_acquired_data(conn):
            while True:
                on_acquisition(conn.recv())

        self.acq_process, child_pipe = Pipe()
        p = Process(
            target=self.connect_acquisition_process,
            args=(child_pipe, use_ssh, host)
        )
        p.start()

        # wait until connection is established
        self.acq_process.recv()

        t = threading.Thread(target=receive_acquired_data, args=(self.acq_process,))
        t.daemon = True
        t.start()

        atexit.register(self.shutdown)

    def connect_acquisition_process(self, pipe, use_ssh, host):
        if use_ssh:
            acquisition_rpyc = rpyc.connect(host, ACQUISITION_PORT)
            acquisition = acquisition_rpyc.root
        else:
            from linien.server.acquisition_process import DataAcquisitionService
            stop_nginx()
            flash_fpga()
            acquisition = DataAcquisitionService()

        # tell the main thread that we're ready
        pipe.send(True)

        # run a loop that listens for acquired data and transmits them
        # to the main thread. Also redirects calls from the main thread
        # to the acquiry process.
        last_hash = None
        while True:
            # check whether the main thread sent a command to the acquiry process
            if pipe.poll():
                data = pipe.recv()
                if data[0] == AcquisitionProcessSignals.SHUTDOWN:
                    break
                elif data[0] == AcquisitionProcessSignals.SET_RAMP_SPEED:
                    speed = data[1]
                    acquisition.exposed_set_ramp_speed(speed)
                elif data[0] == AcquisitionProcessSignals.SET_LOCK_STATUS:
                    acquisition.exposed_set_lock_status(data[1])

            # load acquired data and send it to the main thread
            current_hash = acquisition.exposed_get_data_hash()

            if current_hash != last_hash:
                last_hash = current_hash

                data = acquisition.exposed_return_data()
                pipe.send(data)

            sleep(0.05)

    def shutdown(self):
        if self.acq_process:
            self.acq_process.send((AcquisitionProcessSignals.SHUTDOWN,))

        start_nginx()

    def set_ramp_speed(self, speed):
        self.acq_process.send((AcquisitionProcessSignals.SET_RAMP_SPEED, speed))

    def lock_status_changed(self, status):
        if self.acq_process:
            self.acq_process.send((AcquisitionProcessSignals.SET_LOCK_STATUS, status))