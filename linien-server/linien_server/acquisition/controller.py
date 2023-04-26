# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

import atexit
import subprocess
import threading
from enum import Enum
from multiprocessing import Pipe, Process
from time import sleep

import rpyc
from linien_common.config import ACQUISITION_PORT
from linien_server.acquisition.service import AcquisitionService
from rpyc.utils.server import ThreadedServer

MAX_CONNECTION_ATTEMPTS = 10


class AcquisitionProcessSignals(Enum):
    SHUTDOWN = 0
    SET_SWEEP_SPEED = 2
    SET_LOCK_STATUS = 3
    SET_CSR = 4
    SET_IIR_CSR = 5
    PAUSE_ACQUISIITON = 5.5
    CONTINUE_ACQUISITION = 6
    FETCH_QUADRATURES = 7
    SET_RAW_ACQUISITION = 8
    SET_DUAL_CHANNEL = 9


class AcquisitionController:
    def __init__(self, host=None):
        self.on_new_data_received = None

        acquisition_server_process = Process(target=self.start_acquisition_server)
        acquisition_server_process.daemon = True
        acquisition_server_process.start()

        self.parent_conn, child_conn = Pipe()
        acqusition_service_process = Process(
            target=self.connect_acquisition_service, args=(child_conn, host)
        )
        acqusition_service_process.daemon = True
        acqusition_service_process.start()

        # wait until connection is established
        self.parent_conn.recv()

        receive_data_thread = threading.Thread(
            target=self.receive_acquired_data, args=(self.parent_conn,)
        )
        receive_data_thread.daemon = True
        receive_data_thread.start()

        atexit.register(self.shutdown)

    def start_acquisition_server(self):
        threaded_server = ThreadedServer(AcquisitionService(), port=ACQUISITION_PORT)
        print("Starting AcquisitionService on port " + str(ACQUISITION_PORT))
        threaded_server.start()

    def receive_acquired_data(self, conn):
        while True:
            is_raw, received_data, data_uuid = conn.recv()
            if self.on_new_data_received is not None:
                self.on_new_data_received(is_raw, received_data, data_uuid)

    def connect_acquisition_service(self, pipe, host="127.0.0.1"):
        print("Connecting AcquisitionService...")
        i = 0
        while i < MAX_CONNECTION_ATTEMPTS:
            try:
                acquisition_rpyc = rpyc.connect(host, ACQUISITION_PORT)
                acquisition_service = acquisition_rpyc.root
                break
            except ConnectionRefusedError:
                print("AcquisitionService not yet established, trying again...")
                i = i + 1
                sleep(1)
        # tell the main thread that we're ready
        pipe.send(True)

        # Run a loop that listens for acquired data and transmits them to the main
        # thread. Also redirects calls from the main thread sto the acquiry process.
        last_hash = None
        while True:
            # check whether the main thread sent a command to the acquiry process
            while pipe.poll():
                data = pipe.recv()
                if data[0] == AcquisitionProcessSignals.SHUTDOWN:
                    raise SystemExit()
                elif data[0] == AcquisitionProcessSignals.SET_SWEEP_SPEED:
                    speed = data[1]
                    acquisition_service.exposed_set_sweep_speed(speed)
                elif data[0] == AcquisitionProcessSignals.SET_LOCK_STATUS:
                    acquisition_service.exposed_set_lock_status(data[1])
                elif data[0] == AcquisitionProcessSignals.FETCH_QUADRATURES:
                    acquisition_service.exposed_set_fetch_additional_signals(data[1])
                elif data[0] == AcquisitionProcessSignals.SET_RAW_ACQUISITION:
                    acquisition_service.exposed_set_raw_acquisition(data[1])
                elif data[0] == AcquisitionProcessSignals.SET_DUAL_CHANNEL:
                    acquisition_service.exposed_set_dual_channel(data[1])
                elif data[0] == AcquisitionProcessSignals.SET_CSR:
                    acquisition_service.exposed_set_csr(*data[1])
                elif data[0] == AcquisitionProcessSignals.SET_IIR_CSR:
                    acquisition_service.exposed_set_iir_csr(*data[1])
                elif data[0] == AcquisitionProcessSignals.PAUSE_ACQUISIITON:
                    acquisition_service.exposed_pause_acquisition()
                elif data[0] == AcquisitionProcessSignals.CONTINUE_ACQUISITION:
                    acquisition_service.exposed_continue_acquisition(data[1])

            # load acquired data and send it to the main thread
            (
                new_data_returned,
                new_hash,
                data_was_raw,
                new_data,
                data_uuid,
            ) = acquisition_service.exposed_return_data(last_hash)
            if new_data_returned:
                last_hash = new_hash
                pipe.send((data_was_raw, new_data, data_uuid))

            sleep(0.05)

    def pause_acquisition(self):
        self.parent_conn.send((AcquisitionProcessSignals.PAUSE_ACQUISIITON, True))

    def continue_acquisition(self, uuid):
        self.parent_conn.send((AcquisitionProcessSignals.CONTINUE_ACQUISITION, uuid))

    def shutdown(self):
        if self.parent_conn:
            self.parent_conn.send((AcquisitionProcessSignals.SHUTDOWN,))
        start_nginx()

    def set_sweep_speed(self, speed):
        self.parent_conn.send((AcquisitionProcessSignals.SET_SWEEP_SPEED, speed))

    def set_lock_status(self, status):
        if self.parent_conn:
            self.parent_conn.send((AcquisitionProcessSignals.SET_LOCK_STATUS, status))

    def fetch_additional_signals(self, status):
        if self.parent_conn:
            self.parent_conn.send((AcquisitionProcessSignals.FETCH_QUADRATURES, status))

    def set_csr(self, key, value):
        self.parent_conn.send((AcquisitionProcessSignals.SET_CSR, (key, value)))

    def set_iir_csr(self, *args):
        self.parent_conn.send((AcquisitionProcessSignals.SET_IIR_CSR, args))

    def set_raw_acquisition(self, enabled, decimation=0):
        self.parent_conn.send(
            (AcquisitionProcessSignals.SET_RAW_ACQUISITION, (enabled, decimation))
        )

    def set_dual_channel(self, enabled):
        self.parent_conn.send((AcquisitionProcessSignals.SET_DUAL_CHANNEL, enabled))


def stop_nginx():
    subprocess.Popen(["systemctl", "stop", "redpitaya_nginx.service"]).wait()
    subprocess.Popen(["systemctl", "stop", "redpitaya_scpi.service"]).wait()


def start_nginx():
    subprocess.Popen(["systemctl", "start", "redpitaya_nginx.service"])
