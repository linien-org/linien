#script to update the server-side linien to use the forked version of linien
#i.e, need to update the gateware, csrmap, server.py, registers.py, parameters.py and communication.py
#as well as linien_common

#!/bin/bash

PITAYA="root@rp-f0edf0.local"
REMOTE="/usr/local/lib/python3.10/dist-packages/linien_server/"
REMOTE_COMMON="/usr/local/lib/python3.10/dist-packages/linien_common/"

echo "Stopping server..."
ssh $PITAYA "linien-server stop"

echo "Copying Files ..."
scp linien-server/linien_server/gateware.bin $PITAYA:$REMOTE/
scp linien-server/linien_server/csrmap.py $PITAYA:$REMOTE/
scp linien-server/linien_server/server.py $PITAYA:$REMOTE/
scp linien-server/linien_server/registers.py $PITAYA:$REMOTE/
scp linien-server/linien_server/parameters.py $PITAYA:$REMOTE/
scp linien-common/linien_common/communication.py $PITAYA:$REMOTE_COMMON/

echo "starting server"
ssh $PITAYA "linien-server start"

echo "done"

