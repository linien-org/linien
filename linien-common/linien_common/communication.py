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

import pickle
from typing import Any


def pack(value: Any) -> bytes:
    try:
        return pickle.dumps(value)
    except TypeError:
        # this happens when un-pickleable objects (e.g. functions) are assigned to a
        # parameter. In this case, we don't pickle it but transfer a netref instead.
        return value


def unpack(value: Any) -> Any:
    try:
        return pickle.loads(value)
    except TypeError:
        return value
