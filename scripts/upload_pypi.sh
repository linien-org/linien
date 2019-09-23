#!/bin/bash

set -e

while true; do
    read -p "Did you remember to build a new gateware (if required)? [y/n]" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH/../

FILE=linien/server/linien.bin

if [ ! -f "$FILE" ]; then
    echo "FPGA binary is missing. Run build_gateware.sh to build it."
    exit
fi

# build client
set +e
rm -R build
rm -R dist
set -e

python3 setup_client.py sdist bdist_wheel
read -s -p "Enter your pypi password: " password
# python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/* -u hermitdemschoenenleben -p $password
python3 -m twine check dist/*
python3 -m twine upload dist/* -u hermitdemschoenenleben -p $password

# build server
rm -R build
rm -R dist
python3 setup_server.py sdist bdist_wheel
echo 'enter pypi password'
# python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/* -u hermitdemschoenenleben -p $password
python3 -m twine check dist/*
python3 -m twine upload dist/* -u hermitdemschoenenleben -p $password