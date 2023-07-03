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

from typing import List, Tuple

from linien_common.influxdb import InfluxDBCredentials
from typing_extensions import Protocol


class LinienControlService(Protocol):
    def exposed_get_server_version(self) -> str:
        ...

    def exposed_get_param(self, param_name: str) -> bytes:
        ...

    def exposed_set_param(self, param_name: str, value: bytes) -> None:
        ...

    def exposed_reset_param(self, param_name: str) -> None:
        ...

    def exposed_init_parameter_sync(self, uuid: str) -> bytes:
        ...

    def exposed_register_remote_listener(self, uuid: str, param_name: str) -> None:
        ...

    def exposed_register_remote_listeners(
        self, uuid: str, param_names: List[str]
    ) -> None:
        ...

    def exposed_get_changed_parameters_queue(self, uuid: str) -> bytes:
        ...

    def exposed_write_registers(self) -> None:
        ...

    def exposed_start_optimization(self, x0, x1, spectrum) -> None:
        ...

    def exposed_start_psd_acquisition(self) -> None:
        ...

    def exposed_start_pid_optimization(self) -> None:
        ...

    def exposed_start_sweep(self) -> None:
        ...

    def exposed_start_lock(self) -> None:
        ...

    def exposed_shutdown(self) -> None:
        ...

    def exposed_pause_acquisition(self) -> None:
        ...

    def exposed_continue_acquisition(self) -> None:
        ...

    def exposed_set_csr_direct(self, key: str, value: int) -> None:
        ...

    def exposed_set_parameter_log(self, param_name: str, value: bool) -> None:
        ...

    def exposed_get_parameter_log(self, param_name: str) -> bool:
        ...

    def exposed_update_influxdb_credentials(
        self, credentials: InfluxDBCredentials
    ) -> Tuple[bool, int, str]:
        ...

    def exposed_get_influxdb_credentials(self) -> bytes:
        ...

    def exposed_start_logging(self, interval: float) -> None:
        ...

    def exposed_stop_logging(self) -> None:
        ...

    def exposed_get_logging_status(self) -> bool:
        ...
