#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $DIR/..

FILE=/etc/resolv.conf
if [ -f "linien/VERSION" ]; then
    pyinstaller client.spec
else 
    echo "VERSION file is missing! See README"
fi