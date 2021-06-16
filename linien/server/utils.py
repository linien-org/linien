import shutil
import subprocess

from linien.config import REMOTE_BASE_PATH


def stop_nginx():
    subprocess.Popen(["systemctl", "stop", "redpitaya_nginx.service"]).wait()
    subprocess.Popen(["systemctl", "stop", "redpitaya_scpi.service"]).wait()


def start_nginx():
    subprocess.Popen(["systemctl", "start", "redpitaya_nginx.service"])


def flash_fpga():
    shutil.copyfile("linien.bin", "/dev/xdevcfg")


def twos_complement(num, N_bits):
    max_ = 1 << (N_bits - 1)
    full = 2 * max_

    if num < 0:
        num += full

    return num


def ramp_speed_to_time(ramp_speed):
    """Ramp speed is an arbitrary unit (cf. `parameters.py`).
    This function converts it to the duration of the ramp in seconds.
    """
    f_real = 3.8e3 / (2 ** ramp_speed)
    duration = 1 / f_real
    return duration