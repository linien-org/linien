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

import logging
import os
import sys

import linien_client
from fabric import Connection
from linien_client.exceptions import (
    InvalidServerVersionException,
    ServerNotInstalledException,
)
from linien_common.communication import hash_username_and_password

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def read_remote_version(
    host: str, user: str, password: str, port: int = 22, out_stream=sys.stdout
) -> str:
    """Read the remote version of linien."""

    if not out_stream:
        # sys.stdout is not available in the pyinstaller build, redirect it to avoid
        # AttributeError: 'NoneType' object has no attribute 'write'
        out_stream = open(os.devnull, "w")

    with Connection(
        host, user=user, port=port, connect_kwargs={"password": password}
    ) as conn:
        result = conn.run(
            'python3 -c "import linien_server; print(linien_server.__version__);"',
            out_stream=out_stream,
            err_stream=out_stream,
            warn=True,
        )
    if result.ok:
        return result.stdout.strip()
    else:
        raise ServerNotInstalledException()


def start_remote_server(
    host: str, user: str, password: str, port: int = 22, out_stream=sys.stdout
) -> None:
    """Start the remote linien server."""

    if not out_stream:
        # sys.stdout is not available in the pyinstaller build, redirect it to avoid
        # AttributeError: 'NoneType' object has no attribute 'write'
        out_stream = open(os.devnull, "w")

    with Connection(
        host, user=user, port=port, connect_kwargs={"password": password}
    ) as conn:
        local_version = linien_client.__version__.split("+")[0]
        remote_version = read_remote_version(host, user, password, port).split("+")[0]

        if (local_version != remote_version) and not ("dev" in local_version):
            raise InvalidServerVersionException(local_version, remote_version)

        logger.debug("Sending credentials")
        conn.run(
            'python3 -c "from linien_common.communication import write_hash_to_file;'
            f"write_hash_to_file('{hash_username_and_password(user, password)}')\"",
            out_stream=out_stream,
            err_stream=out_stream,
            warn=True,
        )

        logger.debug("Starting server")
        conn.run(
            "linien_start_server.sh",
            out_stream=out_stream,
            err_stream=out_stream,
            warn=True,
        )


def install_remote_server(
    host: str, user: str, password: str, port: int = 22, out_stream=sys.stdout
):
    """Install the remote linien server."""

    if not out_stream:
        # sys.stdout is not available in the pyinstaller build
        out_stream = open(os.devnull, "w")

    with Connection(
        host, user=user, port=port, connect_kwargs={"password": password}
    ) as conn:
        local_version = linien_client.__version__.split("+")[0]
        cmds = [
            "linien_stop_server.sh",
            "pip3 uninstall linien-server -y",
            "pip3 uninstall linien-common -y",
            f"pip3 install linien-server=={local_version} --no-cache-dir",
            "linien_install_requirements.sh",
        ]
        for cmd in cmds:
            out_stream.write(f">> {cmd}\n")
            result = conn.run(
                cmd, out_stream=out_stream, err_stream=out_stream, warn=True
            )
            if result.ok:
                logger.debug(f"Sucesfully executed '{result.command}'")
