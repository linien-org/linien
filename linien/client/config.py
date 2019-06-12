import os
import pickle
import appdirs


def get_data_folder():
    folder_name = appdirs.user_data_dir('linien')

    if not os.path.exists(folder_name):
        os.mkdir(folder_name)

    return folder_name


def get_devices_filename():
    return os.path.join(
        get_data_folder(),
        'devices'
    )


def save_device_data(devices):
    with open(get_devices_filename(), 'wb') as f:
        pickle.dump(devices, f)


def load_device_data():
    try:
        with open(get_devices_filename(), 'rb') as f:
            devices = pickle.load(f)
    except FileNotFoundError:
        devices = []

    return devices