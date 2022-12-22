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

import sys

import linien_client
from fabric import Connection
from linien_client.exceptions import (
    InvalidServerVersionException,
    ServerNotInstalledException,
)


def read_remote_version(conn: Connection) -> str:
    """Read the remote version of linien."""
    result = conn.run(
        'python3 -c "import linien_server; print(linien_server.__version__);"'
    )
    if result.ok:
        return result.stdout.strip()
    else:
        raise ServerNotInstalledException()


def start_remote_server(host: str, user: str, password: str, port: int = 22):
    with Connection(
        host, user=user, port=port, connect_kwargs={"password": password}
    ) as conn:

        local_version = linien_client.__version__

        remote_version = read_remote_version(conn)

        if local_version != remote_version:
            if "dev" in local_version:
                print("Local version is dev version, skipping version check.")
                print(
                    f"Remote version: {remote_version}, local version: {local_version}"
                )
            else:
                raise InvalidServerVersionException(local_version, remote_version)

        # start the server process
        conn.run("linien_start_server.sh")


def install_remote_server(
    host: str, user: str, password: str, port: int = 22, out_stream=sys.stdout
):
    with Connection(
        host, user=user, port=port, connect_kwargs={"password": password}
    ) as conn:
        cmds = ["ping 0 -c 3"]
        for cmd in cmds:
            out_stream.write(f">>{cmd}")
            result = conn.run(cmd, out_stream=out_stream)
        if result.ok:
            print(f"Sucesfully executed '{result.command}'")
