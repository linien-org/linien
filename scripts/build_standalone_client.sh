#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $DIR/..

while true; do
    read -p "Did you update your VERSION file? " yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

pwd
requirements=$(cat client_requirements)
python3.8 -m pip install $requirements --user

pyinstaller client.spec
FILE=/etc/resolv.conf
if [ -f "linien/VERSION" ]; then
    pyinstaller client.spec
else
    echo "VERSION file is missing! See README"
fi
