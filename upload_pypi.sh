#!/bin/bash

set -e

read -p "Use production pypi.org? [y/n]" realpypi

while true; do
    read -p "Did you remember to build a new gateware (if required)? [y/n]" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

while true; do
    read -p "Did you update your VERSION file? [y/n]" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH

FILE=linien-server/linien_server/linien.bin

if [ ! -f "$FILE" ]; then
    echo "FPGA binary is missing. Run build_gateware.sh to build it."
    exit
fi

read -s -p "Enter your pypi token: " token

# COMMON
cd $SCRIPTPATH/linien-common
python3 setup.py sdist bdist_wheel
python3 -m twine check dist/*

case $realpypi in
    [Yy]* ) python3 -m twine upload dist/* -u __token__ -p $token;;
    * ) python3 -m twine upload --repository testpypi dist/* -u __token__ -p $token;;
esac


# CLIENT
cd $SCRIPTPATH/linien-client
python3 setup.py sdist bdist_wheel
python3 -m twine check dist/*

case $realpypi in
    [Yy]* ) python3 -m twine upload dist/* -u __token__ -p $token;;
    * ) python3 -m twine upload --repository testpypi dist/* -u __token__ -p $token;;
esac


# GUI
cd $SCRIPTPATH/linien-gui
python3 setup.py sdist bdist_wheel
python3 -m twine check dist/*

case $realpypi in
    [Yy]* ) python3 -m twine upload dist/* -u __token__ -p $token;;
    * ) python3 -m twine upload --repository testpypi dist/* -u __token__ -p $token;;
esac


# SERVER
cd $SCRIPTPATH/linien-server
python3 setup.py sdist bdist_wheel
python3 -m twine check dist/*

case $realpypi in
    [Yy]* ) python3 -m twine upload dist/* -u __token__ -p $token;;
    * ) python3 -m twine upload --repository testpypi dist/* -u __token__ -p $token;;
esac
