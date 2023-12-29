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
from typing import Optional

import click
from linien_common.common import no_authenticator, username_and_password_authenticator
from linien_common.config import DEFAULT_SERVER_PORT
from linien_server import __version__, mdio_tool
from rpyc.utils.server import ThreadedServer

from .server import FakeRedPitayaControlService, RedPitayaControlService

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@click.command("linien-server")
@click.version_option(__version__)
@click.argument("port", default=DEFAULT_SERVER_PORT, type=int, required=False)
@click.option(
    "--fake", is_flag=True, help="Runs a fake server that just returns random data"
)
@click.option(
    "--host",
    help=(
        "Allows to run the server locally for development and connects to a RedPitaya. "
        "Specify the RP's host as follows: --host=rp-f0xxxx.local"
    ),
)
@click.option("--no-auth", is_flag=True, help="Disable authentication")
def run_server(
    port: int = DEFAULT_SERVER_PORT,
    fake: bool = False,
    host: Optional[str] = None,
    no_auth: bool = False,
):
    logger.info(f"Start server on port {port}")

    if fake:
        logger.info("Starting fake server")
        control = FakeRedPitayaControlService()
    else:
        control = RedPitayaControlService(host=host)

    if no_auth or fake:
        authenticator = no_authenticator
    else:
        authenticator = username_and_password_authenticator

    try:
        mdio_tool.disable_ethernet_blinking()
        thread = ThreadedServer(
            control,
            port=port,
            authenticator=authenticator,
            protocol_config={"allow_pickle": True, "allow_public_attrs": True},
        )
        thread.start()
    finally:
        mdio_tool.enable_ethernet_blinking()


if __name__ == "__main__":
    run_server()
