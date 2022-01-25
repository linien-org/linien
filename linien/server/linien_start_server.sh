#!/bin/bash

# now, we have to find out which folder linien is installed to.
# We do this dynamically in order to be able to detect installations done
# with pip and those that are copied to /linien (in development mode).
# In dev mode, this script is started in the parent folder of the code,
# therefore, the dev code is preferred over any global installation.
pth=`python3 -c 'import linien; print(linien.__path__[0]);'`

# quit any remaining screen session
if [ -x "$(command -v linien_stop_server)" ]; then
    linien_stop_server
fi
screen -X -S linien-server quit
# start a new one
screen -S linien-server -d -m

# start the server inside the screen session
screen -r linien-server -X stuff $"cd $pth/server;\n"

screen -r linien-server -X stuff $"bash linien_stop_ethernet_blinking; python3 server.py $1; bash linien_start_ethernet_blinking; \n"