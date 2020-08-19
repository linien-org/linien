#!/bin/bash
set -e

SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH/../

python3 make.py

rm linien/server/linien.bin -f
cp fpga_build/linien.bin linien/server