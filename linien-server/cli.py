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
from typing import Optional

import click
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


@click.command("linien-server")
@click.version_option(__version__)
@click.option(
    "--fake", is_flag=True, help="Runs a fake server that just returns random data"
)
@click.option(
    "--host",
    help=(
        "Allows to run the server locally for development and connects to a RedPitaya. "
        "Specify the RP's host as follows: '--host=rp-f0xxxx.local'. On the RedPitaya, "
        "the AcquisitionService has to be started manually by calling acqusition.py."
    ),
)
def run_server(fake: bool = False, host: Optional[str] = None):
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


if __name__ == "__main__":
    run_server()
