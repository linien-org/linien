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


class InfluxDBCredentials:
    def __init__(
        self,
        url: str = "http://localhost",
        port: int = 8086,
        org: str = "my-org",
        token: str = "my-token",
        bucket: str = "my-bucket",
        measurement: str = "my-measurement",
    ):
        self.url = url
        self.port = port
        self.org = org
        self.token = token
        self.bucket = bucket
        self.measurement = measurement
