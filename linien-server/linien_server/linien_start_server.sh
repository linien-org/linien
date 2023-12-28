#!/bin/bash

# quit any remaining screen session
linien_stop_server.sh

screen -dmS linien-server bash -c "linien-server"