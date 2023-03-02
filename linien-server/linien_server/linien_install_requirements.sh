#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# the server is started in a screen session
echo 'installing screen...'
apt-get install screen

# https://github.com/RedPitaya/RedPitaya/issues/205
cd /tmp
echo 'building ethernet blinking fix'
git clone https://github.com/linien-org/mdio-tool.git
cd mdio-tool
git checkout 72bd5a915ff046a59ce4303c8de672e77622a86c
cmake .
make
mv -f mdio-tool /usr/bin