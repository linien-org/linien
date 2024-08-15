# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException
from linien_common.communication import ParameterValues
from linien_common.influxdb import InfluxDBCredentials, save_credentials
from linien_server.parameters import Parameters


class InfluxDBLogger:
    def __init__(
        self, credentials: InfluxDBCredentials, parameters: Parameters
    ) -> None:
        self.credentials: InfluxDBCredentials = credentials
        self.parameters: Parameters = parameters
        self.stop_event = Event()
        self.stop_event.set()
        self.update_connection()

    @property
    def credentials(self) -> InfluxDBCredentials:
        return self._credentials

    @credentials.setter
    def credentials(self, value: InfluxDBCredentials) -> None:
        self._credentials = value
        save_credentials(value)

    def update_connection(self) -> InfluxDBClient:
        client = InfluxDBClient(
            url=self.credentials.url,
            token=self.credentials.token,
            org=self.credentials.org,
        )
        self.write_api = client.write_api(write_options=SYNCHRONOUS)

    def start_logging(self, interval: float) -> None:
        conn_success, message = self.test_connection(self.credentials)
        self.thread = Thread(
            target=self._logging_loop,
            args=(interval,),
            daemon=True,
        )
        if conn_success:
            self.stop_event.clear()
            self.thread.start()
        else:
            raise ConnectionError(f"Failed to connect to InfluxDB database: {message}")

    def stop_logging(self) -> None:
        self.stop_event.set()
        self.thread.join()

    def _logging_loop(self, interval: float) -> None:
        while not self.stop_event.is_set():
            data = {}
            for name, param in self.parameters:
                if param.log:
                    if name == "signal_stats":
                        for stat_name, stat_value in param.value.items():
                            data[stat_name] = stat_value
                    else:
                        data[name] = param.value
            self.write_data(self.credentials, data)
            sleep(interval)

    def test_connection(self, credentials: InfluxDBCredentials) -> tuple[bool, str]:
        """Write empty data to the server to test the connection"""
        client = InfluxDBClient(
            url=credentials.url,
            token=credentials.token,
            org=credentials.org,
        )

        health = client.health()
        message = health.message
        success = health.status == "pass"
        if success:
            try:
                client.write_api(write_options=SYNCHRONOUS).write(
                    bucket=credentials.bucket,
                    org=credentials.org,
                    record={
                        "measurement": credentials.measurement,
                        "fields": {},
                    },
                )
            except ApiException as e:
                success = False
                message = e.message
            except Exception:
                success = False
                message = "Exception occurred. Check server log file for details."

        return success, message

    def write_data(
        self, credentials: InfluxDBCredentials, fields: dict[str, ParameterValues]
    ) -> None:
        """Write data to the database"""
        self.write_api.write(
            bucket=credentials.bucket,
            org=credentials.org,
            record={
                "measurement": credentials.measurement,
                "fields": fields,
            },
        )
