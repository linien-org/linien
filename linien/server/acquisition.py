import sys
sys.path += ['../../']
import rpyc
import atexit
import threading

from enum import Enum
from time import sleep
from multiprocessing import Process, Pipe

from linien.config import ACQUISITION_PORT
from linien.server.utils import start_acquisition_process, stop_nginx, \
    start_nginx, flash_fpga


class AcquisitionConnectionError(Exception):
    pass


class AcquisitionProcessSignals(Enum):
    SHUTDOWN = 0
    SET_ASG_OFFSET = 1
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
            pitaya_rpyc = rpyc.connect(host, ACQUISITION_PORT)
        else:
            for i in range(2):
                try:
                    pitaya_rpyc = rpyc.connect('127.0.0.1', ACQUISITION_PORT)
                except:
                    if i == 0:
                        stop_nginx()
                        flash_fpga()
                        start_acquisition_process()

                        # FIXME: shorter?
                        sleep(2)
                    else:
                        raise AcquisitionConnectionError()

        # tell the main thread that we're ready
        pipe.send(True)

        # run a loop that listens for acquired data and transmits them
        # to the main thread. Also redirects calls from the main thread
        # to the acquiry process.
        while True:
            # check whether the main thread sent a command to the acquiry process
            if pipe.poll():
                data = pipe.recv()
                if data[0] == AcquisitionProcessSignals.SHUTDOWN:
                    break
                elif data[0] == AcquisitionProcessSignals.SET_ASG_OFFSET:
                    idx, value = data[1:]
                    pitaya_rpyc.root.set_asg_offset(idx, value)
                elif data[0] == AcquisitionProcessSignals.SET_RAMP_SPEED:
                    speed = data[1]
                    pitaya_rpyc.root.set_ramp_speed(speed)
                elif data[0] == AcquisitionProcessSignals.SET_LOCK_STATUS:
                    pitaya_rpyc.root.set_lock_status(data[1])

            # load acquired data and send it to the main thread
            data = pitaya_rpyc.root.return_data()
            pipe.send(data)

            sleep(0.05)

    def shutdown(self):
        if self.acq_process:
            self.acq_process.send((AcquisitionProcessSignals.SHUTDOWN,))

        start_nginx()

    def set_asg_offset(self, idx, offset):
        self.acq_process.send((AcquisitionProcessSignals.SET_ASG_OFFSET, idx, offset))

    def set_ramp_speed(self, speed):
        self.acq_process.send((AcquisitionProcessSignals.SET_RAMP_SPEED, speed))

    def lock_status_changed(self, status):
        if self.acq_process:
            self.acq_process.send((AcquisitionProcessSignals.SET_LOCK_STATUS, status))