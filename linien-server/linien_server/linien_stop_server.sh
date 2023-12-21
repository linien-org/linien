#!/bin/bash

# Close screen session and start ethernet blinking again, see https://github.com/RedPitaya/RedPitaya/issues/205
screen -XS linien-server quit
mdio-tool w eth0 0x1b 0x0f00