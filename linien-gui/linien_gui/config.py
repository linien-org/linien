# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
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
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator, Tuple

from linien_common.config import USER_DATA_PATH

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

UI_PATH = Path(__file__).parents[0].resolve() / "ui"

# don't plot more often than once per `DEFAULT_PLOT_RATE_LIMIT` seconds
DEFAULT_PLOT_RATE_LIMIT = 0.1

DEFAULT_COLORS = [
    (200, 0, 0, 200),
    (0, 200, 0, 200),
    (0, 0, 200, 200),
    (200, 200, 0, 200),
    (200, 0, 200, 200),
]
N_COLORS = len(DEFAULT_COLORS)


class Color(Enum):
    SPECTRUM1 = 0
    SPECTRUM2 = 1
    SPECTRUM_COMBINED = 2
    CONTROL_SIGNAL = 0
    CONTROL_SIGNAL_HISTORY = 1
    SLOW_HISTORY = 3
    MONITOR_SIGNAL_HISTORY = 4


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

    def add_callback(self, function: Callable, call_immediatly: bool = True):
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
        self.plot_color_0 = Setting(start=DEFAULT_COLORS[0])
        self.plot_color_1 = Setting(start=DEFAULT_COLORS[1])
        self.plot_color_2 = Setting(start=DEFAULT_COLORS[2])
        self.plot_color_3 = Setting(start=DEFAULT_COLORS[3])
        self.plot_color_4 = Setting(start=DEFAULT_COLORS[4])

        # save changed settings to disk
        for _, setting in self:
            setting.add_callback(lambda _: save_settings(self), call_immediatly=False)

    def __iter__(self) -> Iterator[Tuple[str, Setting]]:
        for name, setting in self.__dict__.items():
            if isinstance(setting, Setting):
                yield name, setting


def save_settings(settings: Settings) -> None:
    data = {name: setting.value for name, setting in settings}
    with open(USER_DATA_PATH / "settings.json", "w") as f:
        json.dump(data, f, indent=0)


def load_settings() -> Settings:
    settings = Settings()
    try:
        with open(USER_DATA_PATH / "settings.json", "r") as f:
            data = json.load(f)
            for name, value in data.items():
                if name in settings.__dict__:
                    getattr(settings, name).value = value
    except FileNotFoundError:
        save_settings(settings)

    return settings
