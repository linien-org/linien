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
# the server is started in a screen session
apt-get install screen

cd /tmp
mkdir linien

echo 'installing pyrp3...'
# install pyrp3
cd /tmp/linien
git clone https://github.com/linien-org/pyrp3.git
cd pyrp3
git checkout f13da68d825ede3091a082edf99339c5ed736bd2
python3 setup.py install

echo 'building monitor...'
# build monitor shared library
cd monitor
make
cp libmonitor.so /usr/lib/

cd /tmp
rm -R /tmp/linien

# https://github.com/RedPitaya/RedPitaya/issues/205
echo 'building ethernet blinking fix'
git clone https://github.com/linien-org/mdio-tool.git
cd mdio-tool
git checkout 72bd5a915ff046a59ce4303c8de672e77622a86c
cmake .
make
rm -f /usr/bin/mdio-tool
mv mdio-tool /usr/bin