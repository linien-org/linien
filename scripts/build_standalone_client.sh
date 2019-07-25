#!/bin/bash
cd ..

while true; do
    read -p "Have you built a new gateware? [y/n]" yn
    case $yn in
        [Yy]* ) pyinstaller client.spec; break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done