#!/bin/bash
set -e

while true; do
    read -p "Did you update your VERSION file? " yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

pwd

FILE=/etc/resolv.conf
if [ -f "linien/VERSION" ]; then
    pyinstaller client.spec
else
    echo "VERSION file is missing! See README"
fi