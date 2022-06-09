#!/bin/bash

# quit any remaining screen session
if [ -x "$(command -v linien_stop_server.sh)" ]; then
    linien_stop_server.sh
fi
screen -X -S linien-server quit
# start a new one
screen -S linien-server -d -m

# start the server inside the screen session
screen -r linien-server -X stuff $"bash linien_stop_ethernet_blinking.sh; server.py $1; bash linien_start_ethernet_blinking.sh; \n"