# Copyright 2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

from threading import Event, Thread
from time import sleep

from linien_common.influxdb import InfluxDBCredentials
from linien_server.parameters import Parameters


class InfluxDBLogger:
    def __init__(
        self, credentials: InfluxDBCredentials, parameters: Parameters
    ) -> None:
        self.credentials = credentials
        self.parameters = parameters
        self.stop_event = Event()

    def start_logging(self, interval: float) -> None:
        print("Starting logging")
        self.stop_event.clear()
        self.thread = Thread(
            target=self._logging_loop,
            args=(interval, self.parameters, self.credentials, self.stop_event),
            daemon=True,
        )
        self.thread.start()

    def stop_logging(self) -> None:
        self.stop_event.set()
        self.thread.join()

    def _logging_loop(
        self,
        interval: float,
        credentials: InfluxDBCredentials,
        parameters: Parameters,
        stop_event: Event,
    ) -> None:
        print("Logging to ", credentials.url)
        while not stop_event.is_set():
            for name, param in parameters:
                if param.log:
                    print("Logging", name, param.value)
            sleep(interval)

    @staticmethod
    def test_connection(credentials: InfluxDBCredentials) -> bool:
        return True
