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

import numpy as np
import paramiko
from plumbum import colors

import linien
from linien.client.exceptions import (
    InvalidServerVersionException,
    ServerNotInstalledException,
)
from linien.common import hash_username_and_password
from linien.config import REMOTE_BASE_PATH


def connect_ssh(host, user, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, password=password)
    return ssh


def run_server(host, user, password, port):
    ssh = connect_ssh(host, user, password)

    version = linien.__version__

    if version == "dev":
        # if we are in a development version, we upload the files from source
        # directory directly to the RP.
        upload_source_code(ssh)

        # start the development code that was just uploaded.
        # For that, go to the parent directory; an import of "linien" then
        # points to that directory instead of any globally installed release
        # version.
        stdin, stdout, stderr = ssh.exec_command(
            ("cd %s/../;" % REMOTE_BASE_PATH)
            + (
                "export LINIEN_AUTH_HASH=%s;"
                % hash_username_and_password(user, password)
            )
            + ("bash %s/server/linien_start_server.sh %d" % (REMOTE_BASE_PATH, port))
        )
        err = stderr.read()
        if err:
            print(colors.red | "Error starting the server")
            print(err)
    else:
        # it is a release and not a dev version.

        # read out version number of the server
        remote_version = read_remote_version(ssh)
        print("remote version", remote_version, "local version", version)

        if version != remote_version:
            raise InvalidServerVersionException(version, remote_version)

        # start the server process using the global command
        ssh.exec_command("linien_start_server.sh")
        ssh.close()


def read_remote_version(ssh):
    """Reads the remote version of linien using SSH."""
    stdin, stdout, stderr = ssh.exec_command(
        'python3 -c "import linien; print(linien.__version__);"'
    )
    lines = stdout.readlines()

    if not lines:
        raise ServerNotInstalledException()

    remote_version = lines[0].strip()
    return remote_version


def upload_source_code(ssh):
    """Uploads the application's source code to the remote server using SFTP."""
    print("uploading dev source code...")

    ftp = ssh.open_sftp()

    directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    if not os.path.exists(os.path.join(directory, "server", "linien.bin")):
        print(
            colors.red | "Error: In order to run the development version, "
            "you need the FPGA bitstream in server/linien.bin! "
            "Consult README to see how you can get one."
        )
        raise Exception("FPGA bitstream missing")

    # upload the code required for running the server
    for dirpath, dirnames, filenames in os.walk(directory):
        # lstrip / so os.path.join does not think dir_path_rel is an absolute path.
        dirpath_rel = dirpath.replace(directory, "").lstrip("/")
        # Change direction of path slashes to work on the RedPitayas Linux system. This
        # is necessary when deploying the server from a Windows machine.
        dirpath_rel = dirpath_rel.lstrip("\\")
        remote_path = os.path.join(REMOTE_BASE_PATH, dirpath_rel)

        remote_path = remote_path.replace("\\", "/")

        if "." in dirpath_rel or "__" in dirpath_rel:
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
