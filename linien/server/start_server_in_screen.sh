#!/bin/bash
screen -X -S spectrolockserver quit
screen -S spectrolockserver -d -m
screen -r spectrolockserver -X stuff $'cd /linien/server\n'
screen -r spectrolockserver -X stuff $'python3 server.py\n'
