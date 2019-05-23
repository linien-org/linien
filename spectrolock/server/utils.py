import subprocess
from linie.config import REMOTE_BASE_PATH


def stop_nginx():
    subprocess.Popen(['systemctl', 'stop', 'redpitaya_nginx.service']).wait()
    subprocess.Popen(['systemctl', 'stop', 'redpitaya_scpi.service']).wait()


def start_nginx():
    subprocess.Popen(['systemctl', 'start', 'redpitaya_nginx.service'])


def start_acquisition_process():
    subprocess.Popen(['python3', REMOTE_BASE_PATH + '/server/acquisition.py'])