#!/bin/bash
set -e

SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
cd $SCRIPTPATH/../

VIVADOPATH=~/xilinx/Vivado/2020.2/bin
if [ ! -d $VIVADOPATH ]
then
echo "vivado path $VIVADOPATH does not exist. Please adapt it in build_fpga_image.sh"
exit 1
fi

export PATH=$VIVADOPATH:$PATH

rm linien-server/linien_server/linien.bin -f
python3 gateware/fpga_image_helper.py