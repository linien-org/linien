#!/bin/bash
cd ..

while true; do
    read -p "Did you update your VERSION file?" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

pyinstaller client.spec