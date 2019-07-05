import os
import pickle
import appdirs


COLORS = {
    'spectroscopy1': (200, 0, 0, 200),
    'spectroscopy2': (0, 200, 0, 200),
    'spectroscopy_combined': (0, 0, 200, 200),
    'control_signal': (200, 0, 0, 200),
    'control_signal_history': (0, 200, 0, 200),
    'slow_history': (200, 200, 0, 200)
}


def get_data_folder():
    folder_name = appdirs.user_data_dir('linien')

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

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


def save_parameter(device_key, param, value, delete=False):
    devices = load_device_data()
    device = [d for d in devices if d['key'] == device_key][0]
    device.setdefault('params', {})

    if not delete:
        device['params'][param] = value
    else:
        try:
            del device['params'][param]
        except KeyError:
            pass

    save_device_data(devices)


def get_saved_parameters(device_key):
    devices = load_device_data()
    device = [d for d in devices if d['key'] == device_key][0]
    device.setdefault('params', {})
    return device['params']