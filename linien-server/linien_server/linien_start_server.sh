#!/bin/bash

# quit any remaining screen session
linien_stop_server.sh

# stop ethernet blinking and start the server inside the screen session. Start ethernet blinking again after server stopped.
# Regarding ethernet blinking, see https://github.com/RedPitaya/RedPitaya/issues/205
screen -dmS linien-server bash -c "mdio-tool w eth0 0x1b 0x0000;linien-server;mdio-tool w eth0 0x1b 0x0f00"