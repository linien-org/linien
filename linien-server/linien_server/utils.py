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

import shutil
import subprocess
from pathlib import Path


def stop_nginx():
    subprocess.Popen(["systemctl", "stop", "redpitaya_nginx.service"]).wait()
    subprocess.Popen(["systemctl", "stop", "redpitaya_scpi.service"]).wait()


def start_nginx():
    subprocess.Popen(["systemctl", "start", "redpitaya_nginx.service"])


def flash_fpga():
    filepath = Path(__file__).parent / "linien.bin"
    shutil.copy(str(filepath.resolve()), "/dev/xdevcfg")


def twos_complement(num, N_bits):
    max_ = 1 << (N_bits - 1)
    full = 2 * max_

    if num < 0:
        num += full

    return num


def sweep_speed_to_time(sweep_speed):
    """Sweep speed is an arbitrary unit (cf. `parameters.py`).
    This function converts it to the duration of the sweep in seconds.
    """
    f_real = 3.8e3 / (2**sweep_speed)
    duration = 1 / f_real
    return duration
