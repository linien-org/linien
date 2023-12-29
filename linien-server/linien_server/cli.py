# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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
from typing import Optional

import fire
from linien_common.communication import (
    no_authenticator,
    username_and_password_authenticator,
)
from linien_server import __version__, mdio_tool
from linien_server.server import (
    FakeRedPitayaControlService,
    RedPitayaControlService,
    run_threaded_server,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LinienServerCLI:
    def version(self) -> str:
        """Return the version of the Linien server."""
        return __version__

    def init(self) -> None:
        """Install the required packages for the Linien server."""
        logger.info("Installing Linien server dependencies")
        subprocess.run(["apt", "install", "-y", "screen"])
        logger.info("Installed Linien server dependencies")

    def start(self) -> None:
        """Start the Linien server in a screen session."""
        self.stop()
        logger.info("Starting Linien server")
        subprocess.run(["screen", "-dmS", "linien-server", "linien-server", "run"])
        logger.info("Started Linien server")

    def stop(self) -> None:
        """Stop the Linien server and its screen session."""
        logger.info("Stopping Linien server")
        subprocess.run(["screen", "-XS", "linien-server", "quit"])
        logger.info("Stopped Linien server")

    def run(self, fake: bool = False, host: Optional[str] = None) -> None:
        """
        Run the Linien server.

        Args:
            fake: Whether to run a fake server.
            host: The hostname of the Red Pitaya.
        """
        if fake:
            control = FakeRedPitayaControlService()
        else:
            control = RedPitayaControlService(host=host)

        if fake or host:
            authenticator = no_authenticator
        else:
            authenticator = username_and_password_authenticator

        try:
            if not (fake or host):  # only available on RP
                mdio_tool.disable_ethernet_blinking()
            run_threaded_server(control, authenticator=authenticator)
        finally:
            if not (fake or host):  # only available on RP
                mdio_tool.enable_ethernet_blinking()


def main() -> None:
    fire.Fire(LinienServerCLI)


if __name__ == "__main__":
    main()
