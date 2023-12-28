#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# the server is started in a screen session
echo 'installing screen...'
apt-get -y install screen
