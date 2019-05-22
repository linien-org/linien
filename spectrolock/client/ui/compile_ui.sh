#!/bin/bash

pyuic5 -x main_window.ui -o main_window.py
pyuic5 -x device_manager.ui -o device_manager.py
pyuic5 -x new_device_dialog.ui -o new_device_dialog.py
