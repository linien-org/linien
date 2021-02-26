import sys

sys.path += ["../../"]
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
    SET_CSR = 4
    SET_IIR_CSR = 5
    PAUSE_ACQUISIITON = 5.5
    CONTINUE_ACQUISITION = 6
    FETCH_QUADRATURES = 7
    SET_RAW_ACQUISITION = 8


class AcquisitionMaster:
    def __init__(self, use_ssh, host):
        self.on_acquisition = None

        def receive_acquired_data(conn):
            while True:
                is_raw, received_data, data_uuid = conn.recv()
                if self.on_acquisition is not None:
                    self.on_acquisition(is_raw, received_data, data_uuid)

        self.acq_process, child_pipe = Pipe()
        p = Process(
            target=self.connect_acquisition_process, args=(child_pipe, use_ssh, host)
        )
        p.daemon = True
        p.start()

        # wait until connection is established
        self.acq_process.recv()

        t = threading.Thread(target=receive_acquired_data, args=(self.acq_process,))
        t.daemon = True
        t.start()

        atexit.register(self.shutdown)

    def run_data_acquisition(self, on_acquisition):
        self.on_acquisition = on_acquisition

    def connect_acquisition_process(self, pipe, use_ssh, host):
        if use_ssh:
            # for debugging, acquisition process may be launched manually on the
            # server and rpyc can be used to connect to it
            acquisition_rpyc = rpyc.connect(host, ACQUISITION_PORT)
            acquisition = acquisition_rpyc.root
        else:
            # this is what happens in production mode
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
            while pipe.poll():
                data = pipe.recv()
                if data[0] == AcquisitionProcessSignals.SHUTDOWN:
                    raise SystemExit()
                elif data[0] == AcquisitionProcessSignals.SET_RAMP_SPEED:
                    speed = data[1]
                    acquisition.exposed_set_ramp_speed(speed)
                elif data[0] == AcquisitionProcessSignals.SET_LOCK_STATUS:
                    acquisition.exposed_set_lock_status(data[1])
                elif data[0] == AcquisitionProcessSignals.FETCH_QUADRATURES:
                    acquisition.exposed_set_fetch_quadratures(data[1])
                elif data[0] == AcquisitionProcessSignals.SET_RAW_ACQUISITION:
                    acquisition.exposed_set_raw_acquisition(data[1])
                elif data[0] == AcquisitionProcessSignals.SET_CSR:
                    acquisition.exposed_set_csr(*data[1])
                elif data[0] == AcquisitionProcessSignals.SET_IIR_CSR:
                    acquisition.exposed_set_iir_csr(*data[1])
                elif data[0] == AcquisitionProcessSignals.PAUSE_ACQUISIITON:
                    acquisition.exposed_pause_acquisition()
                elif data[0] == AcquisitionProcessSignals.CONTINUE_ACQUISITION:
                    acquisition.exposed_continue_acquisition(data[1])

            # load acquired data and send it to the main thread
            (
                new_data_returned,
                new_hash,
                data_was_raw,
                new_data,
                data_uuid,
            ) = acquisition.exposed_return_data(last_hash)
            if new_data_returned:
                last_hash = new_hash
                pipe.send((data_was_raw, new_data, data_uuid))

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

    def fetch_quadratures_changed(self, status):
        if self.acq_process:
            self.acq_process.send((AcquisitionProcessSignals.FETCH_QUADRATURES, status))

    def set_csr(self, key, value):
        self.acq_process.send((AcquisitionProcessSignals.SET_CSR, (key, value)))

    def set_iir_csr(self, *args):
        self.acq_process.send((AcquisitionProcessSignals.SET_IIR_CSR, args))

    def pause_acquisition(self):
        self.acq_process.send((AcquisitionProcessSignals.PAUSE_ACQUISIITON, True))

    def continue_acquisition(self, uuid):
        self.acq_process.send((AcquisitionProcessSignals.CONTINUE_ACQUISITION, uuid))

    def set_raw_acquisition(self, enabled, decimation=None):
        if decimation is None:
            decimation = 0
        self.acq_process.send(
            (AcquisitionProcessSignals.SET_RAW_ACQUISITION, (enabled, decimation))
        )
