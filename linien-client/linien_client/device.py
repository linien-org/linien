# Copyright 2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

import json
import logging
import random
import string
from dataclasses import asdict, dataclass, field
from typing import Dict, List

from linien_common.communication import PathLike, RestorableParameterValues
from linien_common.config import SERVER_PORT, USER_DATA_PATH

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def generate_random_key():
    """Generate a random key for the device."""
    return "".join(random.choice(string.ascii_lowercase) for _ in range(10))


@dataclass
class Device:
    """A device that can be connected to."""

    key: str = field(default_factory=generate_random_key)
    name: str = field(default_factory=str)
    host: str = field(default_factory=str)
    port: int = SERVER_PORT
    username: str = field(default_factory=str)
    password: str = field(default_factory=str)
    parameters: Dict[str, RestorableParameterValues] = field(default_factory=dict)

    def __post_init__(self):
        if self.host == "":
            self.host = "rp-xxxxxx.local"
        if self.username == "":
            self.username = "root"
        if self.password == "":
            self.password = "root"
        # FIXME: is this even necessary?
        if self.host in ("localhost", "127.0.0.1"):
            # RP is configured such that "localhost" doesn't point to 127.0.0.1 in all
            # cases
            self.host = "127.0.0.1"

    def __eq__(self, other):
        if isinstance(other, Device):
            return self.key == other.key
        else:
            return False


def add_device(
    device: Device, path: PathLike = USER_DATA_PATH / "devices.json"
) -> None:
    """Add a new device to the device list and save it to disk."""
    devices = load_device_list(path)
    if device in devices:
        raise KeyError(f"Device with key {device.key} already exists in {path}.")
    devices.append(device)
    save_device_list(devices, path)
    logger.debug(f"Added device with key {device.key} to {path}.")


def load_device(key: str, path: PathLike) -> Device:
    """Load a device from disk."""
    devices = load_device_list(path)
    for device in devices:
        if device.key == key:
            return device
    raise KeyError(f"Device with key {key} doesn't exist in {path}.")


def delete_device(
    device: Device, path: PathLike = USER_DATA_PATH / "devices.json"
) -> None:
    """Remove a device from the device list and save it to disk."""
    devices = load_device_list(path)
    devices.remove(device)
    save_device_list(devices, path)


def update_device(
    device: Device, path: PathLike = USER_DATA_PATH / "devices.json"
) -> None:
    """Update a device in the device list and save it to disk."""
    devices = load_device_list(path)
    if device not in devices:
        raise KeyError(f"Device with key {device.key} doesn't exist in {path}.")
    # this updates since equality is defined by the device key, see Device.__eq__
    devices[devices.index(device)] = device
    save_device_list(devices, path)
    logger.debug(f"Updated device with key {device.key} in {path}.")


def move_device(device: Device, direction: int) -> None:
    """Move a device in the device list and save it to disk."""
    devices = load_device_list()
    current_index = devices.index(device)
    new_index = current_index + direction
    devices.insert(new_index, devices.pop(current_index))
    save_device_list(devices)


def save_device_list(
    devices: List[Device], path: PathLike = USER_DATA_PATH / "devices.json"
) -> None:
    """Save a device list to disk."""
    with open(path, "w") as f:
        logger.debug(f"Saving devices to {path}.")
        json.dump({i: asdict(device) for i, device in enumerate(devices)}, f, indent=2)


def load_device_list(
    path: PathLike = USER_DATA_PATH / "devices.json",
) -> List[Device]:
    """Load the device list from disk."""
    try:
        with open(path, "r") as f:
            logger.debug(f"Loading devices from {path}.")
            devices = [Device(**value) for _, value in json.load(f).items()]
    except FileNotFoundError:
        logger.debug("No devices.json found. Return empty list.")
        devices = []
    return devices
