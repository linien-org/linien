#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

while ! ping -c 1 -W 1 8.8.4.4; do
   echo "Not connected to the internet! RedPitaya needs to access the internet in order to proceed with the installation."
   sleep 1
done

echo 'installing dependencies...'
echo 'installing screen...'
# the server is started in a screen session
apt-get install screen

# https://github.com/RedPitaya/RedPitaya/issues/205
cd /tmp
echo 'building ethernet blinking fix'
git clone https://github.com/linien-org/mdio-tool.git
cd mdio-tool
cmake .
make
rm -f /usr/bin/mdio-tool
mv mdio-tool /usr/bin