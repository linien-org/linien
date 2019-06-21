#!/bin/bash
SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH/../

python3 make.py

rm linien/server/redpid.bin
cp fpga_build/redpid.bin linien/server