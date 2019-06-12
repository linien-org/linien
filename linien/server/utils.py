import shutil
import subprocess

from linien.config import REMOTE_BASE_PATH


def stop_nginx():
    subprocess.Popen(['systemctl', 'stop', 'redpitaya_nginx.service']).wait()
    subprocess.Popen(['systemctl', 'stop', 'redpitaya_scpi.service']).wait()


def start_nginx():
    subprocess.Popen(['systemctl', 'start', 'redpitaya_nginx.service'])


def start_acquisition_process():
    subprocess.Popen(['python3', REMOTE_BASE_PATH + '/server/acquisition_process.py'])


def flash_fpga():
    shutil.copyfile('redpid.bin', '/dev/xdevcfg')