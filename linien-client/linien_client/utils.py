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
import numpy as np
import paramiko
from linien_client.exceptions import (
    InvalidServerVersionException,
    ServerNotInstalledException,
)
from linien_common.common import hash_username_and_password
from linien_common.config import REMOTE_DEV_PATH


def connect_ssh(host, user, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, password=password)
    return ssh


def run_server(host, user, password, port):
    ssh = connect_ssh(host, user, password)

    version = linien_client.__version__

    if "dev" in version:
        # If we are in a development version, we upload the files from source directory
        # directly to the RP.
        upload_source_code(ssh)

        # Install the development version in editable mode via pip
        print("Installing development version of linien-common and linien-server")
        _, _, stderr = ssh.exec_command(
            f"""
            export LINIEN_AUTH_HASH={hash_username_and_password(user, password)};
            pip3 install -e {REMOTE_DEV_PATH}/linien-common;
            pip3 install -e {REMOTE_DEV_PATH}/linien-server;
            "bash linien_install_requirements.sh;"
            """
        )

    # read out version number of the server
    remote_version = read_remote_version(ssh)
    print("remote version", remote_version, "local version", version)

    if version != remote_version:
        raise InvalidServerVersionException(version, remote_version)

    # start the server process using the global command
    ssh.exec_command("linien_start_server.sh")
    ssh.close()


def read_remote_version(ssh):
    """Read the remote version of linien using SSH."""
    _, stdout, _ = ssh.exec_command(
        'python3 -c "import linien_server; print(linien_server.__version__);"'
    )
    lines = stdout.readlines()

    if not lines:
        raise ServerNotInstalledException()

    remote_version = lines[0].strip()
    return remote_version


def upload_source_code(ssh):
    """Upload the application's source code to the remote server using SFTP."""

    ftp = ssh.open_sftp()
    repo_root_dir = Path(__file__).parents[2].resolve()
    print("Uploading dev source code...")
    # upload the code required for running the server
    for pkg in ["linien-common", "linien-server"]:
        for dirpath, _, filenames in os.walk(repo_root_dir / pkg):
            # lstrip / so os.path.join does not think dir_path_rel is an absolute path.
            dirpath_rel = dirpath.replace(str(repo_root_dir), "").lstrip("/")
            # Change direction of path slashes to work on the RedPitayas Linux system.
            # This is necessary when deploying the server from a Windows machine.
            dirpath_rel = dirpath_rel.lstrip("\\")
            remote_path = os.path.join(REMOTE_DEV_PATH, dirpath_rel)
            remote_path = remote_path.replace("\\", "/")

            if any(s in dirpath_rel for s in ["__", "."]):
                continue

            try:
                ftp.lstat(remote_path)
            except IOError:
                ftp.mkdir(os.path.join(remote_path.rstrip("/")))

            for filename in filenames:
                local_path = os.path.join(dirpath, filename)
                remote_filepath = os.path.join(remote_path, filename)
                remote_filepath = remote_filepath.replace("\\", "/")
                # put file
                ftp.put(local_path, remote_filepath)

    ftp.close()


def peak_voltage_to_dBm(voltage):
    return 10 + 20 * np.log10(voltage)
