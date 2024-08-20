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
import logging
from pathlib import Path

from appdirs import AppDirs

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ACQUISITION_PORT = 19321
SERVER_PORT = 18862
DEFAULT_SWEEP_SPEED = (125 * 2048) << 6

USER_DATA_PATH = Path(AppDirs("linien").user_data_dir)
USER_DATA_PATH.mkdir(parents=True, exist_ok=True)

LOG_FILE_PATH = USER_DATA_PATH / "linien.log"
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)


def create_backup_file(filename: Path) -> None:
    """Rename the file to a unique filename."""
    i = 0
    while True:
        backup_filename = filename.parent / f"{filename.stem}.backup{i}"
        if not backup_filename.exists():
            break
        i += 1

    filename.rename(backup_filename)
    logger.info(f"{filename} has been saved as {backup_filename}.")
