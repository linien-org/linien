#!/bin/bash
set -e

SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH/../

VIVADOPATH=/tools/Xilinx/Vivado/2020.1/bin
if [ ! -d $VIVADOPATH ]
then
echo "vivado path $VIVADOPATH does not exist. Please adapt it in build_gateware.sh"
exit 1
fi

export PATH=$VIVADOPATH:$PATH

python3 make.py

rm linien/server/linien.bin -f
cp fpga_build/linien.bin linien/server