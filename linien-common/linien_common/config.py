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

from pathlib import Path

from appdirs import AppDirs

ACQUISITION_PORT = 19321
DEFAULT_SERVER_PORT = 18862
DEFAULT_SWEEP_SPEED = (125 * 2048) << 6

USER_DATA_PATH = Path(AppDirs("linien").user_data_dir)
USER_DATA_PATH.mkdir(parents=True, exist_ok=True)

LOG_FILE_PATH = USER_DATA_PATH / "linien.log"
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
