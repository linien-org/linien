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

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def enable_ethernet_blinking() -> None:
    """
    Enable the blinking of the ethernet LEDs.

    See https://github.com/RedPitaya/RedPitaya/issues/205 for details.
    """
    binary_path = Path(__file__).parent / "mdio-tool"
    logger.info(f"Enabling ethernet blinking with mdio-tool at {binary_path}")
    subprocess.run([f"{binary_path}", "w", "eth0", "0x1b", "0x0f00"])


def disable_ethernet_blinking() -> None:
    """
    Disable the blinking of the ethernet LEDs.

    See https://github.com/RedPitaya/RedPitaya/issues/205 for details.
    """
    binary_path = Path(__file__).parent / "mdio-tool"
    logger.info(f"Disabling ethernet blinking with mdio-tool at {binary_path}")
    subprocess.run([f"{binary_path}", "w", "eth0", "0x1b", "0x0000"])
