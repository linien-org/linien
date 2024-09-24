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

from enum import IntEnum, auto


class FilterType(IntEnum):
    LOW_PASS = 0
    HIGH_PASS = 1


class OutputChannel(IntEnum):
    FAST_OUT1 = 0
    FAST_OUT2 = 1
    ANALOG_OUT0 = 2


class AutolockMode(IntEnum):
    AUTO_DETECT = 0
    ROBUST = 1
    SIMPLE = 2


class AutolockStatus(IntEnum):
    FAILED = auto()
    STOPPED = auto()
    SELECTING = auto()
    LOCKING = auto()
    LOCKED = auto()
    RELOCKING = auto()


class PSDAlgorithm(IntEnum):
    WELCH = 0
    LPSD = 1
