import os
import pickle
import appdirs


COLORS = {
    "spectrum_1": 0,
    "spectrum_2": 1,
    "spectrum_combined": 2,
    "control_signal": 0,
    "control_signal_history": 1,
    "slow_history": 3,
}
# don't plot more often than once per `DEFAULT_PLOT_RATE_LIMIT` seconds
DEFAULT_PLOT_RATE_LIMIT = 0.1


def get_data_folder():
    folder_name = appdirs.user_data_dir("linien")

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    return folder_name


def get_devices_filename():
    return os.path.join(get_data_folder(), "devices")


def save_device_data(devices):
    with open(get_devices_filename(), "wb") as f:
        pickle.dump(devices, f)


def load_device_data():
    try:
        with open(get_devices_filename(), "rb") as f:
            devices = pickle.load(f)
    except (FileNotFoundError, pickle.UnpicklingError, EOFError):
        devices = []

    return devices


def save_parameter(device_key, param, value, delete=False):
    devices = load_device_data()
    device = [d for d in devices if d["key"] == device_key][0]
    device.setdefault("params", {})

    if not delete:
        device["params"][param] = value
    else:
        try:
            del device["params"][param]
        except KeyError:
            pass

    save_device_data(devices)


def get_saved_parameters(device_key):
    devices = load_device_data()
    device = [d for d in devices if d["key"] == device_key][0]
    device.setdefault("params", {})
    return device["params"]
