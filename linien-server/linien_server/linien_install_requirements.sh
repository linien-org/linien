#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Copy systemd service file to a location systemd recognizes
cp -f /usr/lib/python3*/site-packages/linien_server/linien.service /usr/lib/systemd/system/linien.service

# https://github.com/RedPitaya/RedPitaya/issues/205
cd /tmp
echo 'building ethernet blinking fix'
git clone https://github.com/linien-org/mdio-tool.git
cd mdio-tool
git checkout v1.0.0
cmake .
make
mv -f mdio-tool /usr/bin
