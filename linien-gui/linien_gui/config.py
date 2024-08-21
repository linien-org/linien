# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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
from pathlib import Path
from typing import Callable, Iterator, Tuple

from linien_common.config import USER_DATA_PATH, create_backup_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

UI_PATH = Path(__file__).parents[0].resolve() / "ui"
SETTINGS_STORE_FILENAME = "settings.json"
# don't plot more often than once per `DEFAULT_PLOT_RATE_LIMIT` seconds
DEFAULT_PLOT_RATE_LIMIT = 0.1


class Setting:
    def __init__(
        self,
        min_=None,
        max_=None,
        start=None,
    ):
        self.min = min_
        self.max = max_
        self._value = start
        self.start = start
        self._callbacks = set()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.min is not None and value < self.min:
            value = self.min
        if self.max is not None and value > self.max:
            value = self.max
        self._value = value

        # We copy it because a listener could remove a listener --> this would cause an
        # error in this loop.
        for callback in self._callbacks.copy():
            callback(value)

    def add_callback(self, function: Callable[..., None], call_immediatly: bool = True):
        """Add a callback function that is called when with each newly set value."""
        self._callbacks.add(function)

        if call_immediatly:
            if self._value is not None:
                function(self._value)

    def remove_callback(self, function):
        if function in self._callbacks:
            self._callbacks.remove(function)


class Settings:
    def __init__(self):
        self.plot_line_width = Setting(start=2, min_=0.1, max_=100)
        self.plot_line_opacity = Setting(start=230, min_=0, max_=255)
        self.plot_fill_opacity = Setting(start=70, min_=0, max_=255)
        self.plot_color_error_combined = Setting(start=(214, 39, 40))
        self.plot_color_error1 = Setting(start=(227, 119, 194))
        self.plot_color_error2 = Setting(start=(148, 103, 189))
        self.plot_color_monitor = Setting(start=(31, 119, 180))
        self.plot_color_monitor_history = Setting(start=(23, 190, 207))
        self.plot_color_control = Setting(start=(188, 189, 34))
        self.plot_color_control_history = Setting(start=(255, 127, 14))
        self.plot_color_slow_control = Setting(start=(44, 160, 44))

        # save changed settings to disk
        for _, setting in self:
            setting.add_callback(lambda _: save_settings(self), call_immediatly=False)

    def __iter__(self) -> Iterator[Tuple[str, Setting]]:
        for name, setting in self.__dict__.items():
            if isinstance(setting, Setting):
                yield name, setting

    @property
    def plot_colors(self) -> list[Setting]:
        all_color_settings = []
        for name, setting in self:
            if name.startswith("plot_color_"):
                all_color_settings.append(setting)
        return all_color_settings


def save_settings(settings: Settings) -> None:
    data = {name: setting.value for name, setting in settings}
    with open(USER_DATA_PATH / SETTINGS_STORE_FILENAME, "w") as f:
        json.dump(data, f, indent=0)


def load_settings() -> Settings:
    settings = Settings()
    filename = USER_DATA_PATH / SETTINGS_STORE_FILENAME
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            for name, value in data.items():
                if name in settings.__dict__:
                    getattr(settings, name).value = value
    except FileNotFoundError:
        save_settings(settings)
    except json.JSONDecodeError:
        logger.error(f"Settings file {filename} was corrupted.")
        create_backup_file(filename)
    return settings
