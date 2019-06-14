#!/bin/bash
SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH/../

FILE=fpga_build/redpid.bin

if [ ! -f "$FILE" ]; then
    echo "FPGA binary is missing. Run build_gateware.sh to build it."
    exit
fi

cp $FILE linien/server/redpid.bin

# build client
#rm -R build
#rm -R dist

#python3 setup_client.py sdist bdist_wheel
#echo 'enter pypi password'
#python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/* -u hermitdemschoenenleben
# python3 -m twine upload dist/* -u hermitdemschoenenleben

# build server
rm -R build
rm -R dist
python3 setup_server.py sdist bdist_wheel
echo 'enter pypi password'
python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/* -u hermitdemschoenenleben
# python3 -m twine upload dist/* -u hermitdemschoenenleben