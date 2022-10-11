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

import os
from pathlib import Path

import linien_client
from fabric import Connection
from linien_client.exceptions import (
    InvalidServerVersionException,
    ServerNotInstalledException,
)
from linien_common.common import hash_username_and_password
from linien_common.config import REMOTE_DEV_PATH
from patchwork.files import exists


def copy_source_code_to_remote(conn: Connection) -> None:
    """Upload the application's source code to the remote server using SFTP."""

    if not exists(conn, REMOTE_DEV_PATH):
        print("Creating remote development directory.")
        conn.run(f"mkdir -p {REMOTE_DEV_PATH}")
    print("Cleaning remote development directory...")
    conn.run(f"rm -rf {REMOTE_DEV_PATH}/*")

    repo_root_dir = Path(__file__).parents[2].resolve()
    print("Copying dev source code to RedPitaya.")
    # upload the code required for running the server
    for dir in ["linien-common", "linien-server", ".git"]:
        print(f"Copying {dir}.")
        for dirpath, _, filenames in os.walk(repo_root_dir / dir):
            # lstrip / so os.path.join does not think dir_path_rel is an absolute path.
            dirpath_rel = dirpath.replace(str(repo_root_dir), "").lstrip("/")
            # Change direction of path slashes to work on the RedPitayas Linux system.
            # This is necessary when deploying the server from a Windows machine.
            dirpath_rel = dirpath_rel.lstrip("\\")
            remote_path = os.path.join(REMOTE_DEV_PATH, dirpath_rel)
            remote_path = remote_path.replace("\\", "/")

            # filter directories that should not be copied
            if "__" in dirpath_rel:
                continue

            if not exists(conn, remote_path):
                conn.run(f"mkdir -p {remote_path}")

            for filename in filenames:
                local_path = os.path.join(dirpath, filename)
                remote_filepath = os.path.join(remote_path, filename)
                remote_filepath = remote_filepath.replace("\\", "/")
                conn.put(local_path, remote_filepath)


def install_dev_version(conn: Connection, user: str, password: str) -> None:
    """
    Install development versions of linien-common and linien-server on the remote.
    """
    print("Installing development version of linien-common and linien-server")
    commands = [
        f"export LINIEN_AUTH_HASH={hash_username_and_password(user, password)}",
        f"pip3 install -e {REMOTE_DEV_PATH}/linien-common",
        f"pip3 install -e {REMOTE_DEV_PATH}/linien-server",
        "bash linien_install_requirements.sh",
    ]
    for cmd in commands:
        result = conn.run(cmd)
        if result.ok:
            print(f"Sucesfully executed '{result.command}'")
        else:
            print(f"Someting went wrong when running '{result.command}'")
            print(result.stdout)


def read_remote_version(conn: Connection) -> str:
    """Read the remote version of linien."""
    result = conn.run(
        'python3 -c "import linien_server; print(linien_server.__version__);"'
    )
    if result.ok:
        return result.stdout.strip()
    else:
        raise ServerNotInstalledException()

    # lines = stdout.readlines()
    # remote_version = lines[0].strip()
    # return remote_version


def deploy_remote_server(host: str, user: str, password: str, port: int = 22):
    with Connection(
        host, user=user, port=port, connect_kwargs={"password": password}
    ) as conn:

        version = linien_client.__version__

        if "dev" in version:
            # If we are in a development version, we upload the files from source
            # directory to the RP and install linien-common and linien-server in
            # editable mode.
            copy_source_code_to_remote(conn)
            install_dev_version(conn, user, password)

        remote_version = read_remote_version(conn)
        print(f"Remote version: {remote_version}, local version: {version}")

        if version != remote_version:
            raise InvalidServerVersionException(version, remote_version)

        # start the server process
        conn.run("linien_start_server.sh")
