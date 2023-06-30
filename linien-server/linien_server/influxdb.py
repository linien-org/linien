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

from copy import deepcopy
from threading import Event, Thread
from time import sleep

import requests
from linien_common.influxdb import InfluxDBCredentials, save_credentials
from linien_server.parameters import Parameters


class InfluxDBLogger:
    def __init__(
        self, credentials: InfluxDBCredentials, parameters: Parameters
    ) -> None:
        self.credentials = credentials
        self.parameters = parameters
        self.stop_event = Event()

    @property
    def credentials(self) -> InfluxDBCredentials:
        return self._credentials

    @credentials.setter
    def credentials(self, value: InfluxDBCredentials) -> None:
        self._credentials = value
        save_credentials(value)

    def start_logging(self, interval: float) -> None:
        if self.test_connection(self.credentials):
            self.stop_event.clear()
            self.thread = Thread(
                target=self._logging_loop,
                args=(interval),
                daemon=True,
            )
            self.thread.start()
        else:
            raise ConnectionError("Failed to connect to InfluxDB server")

    def stop_logging(self) -> None:
        self.stop_event.set()
        self.thread.join()

    def _logging_loop(self, interval: float) -> None:
        while not self.stop_event.is_set():
            data = {}
            parameters = deepcopy(self.parameters)
            for name, param in parameters:
                if param.log:
                    if name == "signal_stats":
                        for stat_name, stat_value in param.value.items():
                            data[stat_name] = stat_value
                    else:
                        data[name] = param.value
            self.write_data(data)
            sleep(interval)

    def test_connection(self) -> bool:
        """Write empty data to the server to test the connection"""
        return self.write_data({}).status_code == 204

    def write_data(self, data: dict) -> requests.Response:
        """Write data to the database"""
        endpoint = self.credentials.url + "/api/v2/write"
        headers = {
            "Authorization": "Token " + self.credentials.token,
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json",
        }
        params = {
            "org": self.credentials.org,
            "bucket": self.credentials.bucket,
            "precision": "ns",
        }

        data = self._convert_to_line_protocol(data)

        response = requests.post(endpoint, headers=headers, params=params, data=data)
        return response

    def _convert_to_line_protocol(self, data: dict) -> str:
        if not data:
            return ""
        point = self.credentials.measurement
        for i, (key, value) in enumerate(data.items()):
            if i == 0:
                point += " "
            else:
                point += ","
            point += "%s=%s" % (key, value)
        return point
