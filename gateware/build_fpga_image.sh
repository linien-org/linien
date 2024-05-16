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

rm linien-server/linien_server/gateware.bin -f
# run with -m option to avoid errors related to relative imports without breaking pytest
python3 -m gateware.fpga_image_helper