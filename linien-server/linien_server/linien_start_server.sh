#!/bin/bash

# quit any remaining screen session
if [ -x "$(command -v linien_stop_server.sh)" ]; then
    linien_stop_server.sh
fi
screen -X -S linien-server quit
# start a new one
screen -S linien-server -d -m

# stop ethernet blinking and start the server inside the screen session. Start ethernet blinking again after server stopped.
# Regarding ethernet blinking, see https://github.com/RedPitaya/RedPitaya/issues/205
screen -r linien-server -X stuff $"mdio-tool w eth0 0x1b 0x0000; linien-server $1; mdio-tool w eth0 0x1b 0x0f00; \n"