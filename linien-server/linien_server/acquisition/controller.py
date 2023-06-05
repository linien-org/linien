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
from threading import Thread
from time import sleep

import rpyc
from linien_common.config import ACQUISITION_PORT


class AcquisitionController:
    def __init__(self, host=None):
        self.on_new_data_received = None

        if host is None:
            # AcquisitionService is imported only on the Red Pitaya since pyrp3 is not
            # available on Windows
            from linien_server.acquisition.service import AcquisitionService

            self.acquisition_service = AcquisitionService()
        else:
            # AcquisitionService has to be started manually on the Red Pitaya
            self.acquisition_service = rpyc.connect(host, ACQUISITION_PORT).root

        acqusition_thread = Thread(target=self.run_acquisition_loop, daemon=True)
        acqusition_thread.start()

        atexit.register(self.shutdown)

    def run_acquisition_loop(self):
        last_hash = None
        while True:
            (
                new_data_returned,
                new_hash,
                data_was_raw,
                new_data,
                data_uuid,
            ) = self.acquisition_service.exposed_return_data(last_hash)
            if new_data_returned:
                last_hash = new_hash
            if self.on_new_data_received is not None:
                self.on_new_data_received(data_was_raw, new_data, data_uuid)
            sleep(0.05)

    def pause_acquisition(self):
        self.acquisition_service.exposed_pause_acquisition()

    def continue_acquisition(self, uuid):
        self.acquisition_service.exposed_continue_acquisition(uuid)

    def shutdown(self):
        start_nginx()
        raise SystemExit()

    def set_sweep_speed(self, speed):
        self.acquisition_service.exposed_set_sweep_speed(speed)

    def set_lock_status(self, status):
        if self.acquisition_service:
            self.acquisition_service.exposed_set_lock_status(status)

    def fetch_additional_signals(self, status):
        if self.acquisition_service:
            self.acquisition_service.exposed_set_fetch_additional_signals(status)

    def set_csr(self, key, value):
        self.acquisition_service.exposed_set_csr(key, value)

    def set_iir_csr(self, *args):
        self.acquisition_service.exposed_set_iir_csr(*args)

    def set_raw_acquisition(self, enabled, decimation=0):
        self.acquisition_service.exposed_set_raw_acquisition((enabled, decimation))

    def set_dual_channel(self, enabled):
        self.acquisition_service.exposed_set_dual_channel(enabled)


def stop_nginx():
    subprocess.Popen(["systemctl", "stop", "redpitaya_nginx.service"]).wait()
    subprocess.Popen(["systemctl", "stop", "redpitaya_scpi.service"]).wait()


def start_nginx():
    subprocess.Popen(["systemctl", "start", "redpitaya_nginx.service"])
