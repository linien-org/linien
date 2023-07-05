# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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


class RPYCAuthenticationException(Exception):
    def __init__(self):
        super().__init__(
            "Invalid credentials passed to LinienClient. Be sure to use the same "
            "username and password as when connecting via SSH."
        )


class ServerNotRunningException(Exception):
    def __init__(self):
        super().__init__(
            "The host was reached but no linien server is running. Use "
            "`autostart_server` if you want to change this."
        )


class InvalidServerVersionException(Exception):
    def __init__(self, client_version, remote_version):
        self.client_version = client_version
        self.remote_version = remote_version

        super().__init__(
            "Version mismatch: Client is %s and server is %s"
            % (client_version, remote_version)
        )


class ServerNotInstalledException(Exception):
    pass


class GeneralConnectionError(Exception):
    pass
