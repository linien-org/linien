## V 0.3.2
- FIX: incompatibility with rpyc==5.0.0
- improved documentation

## V 0.3.1
- FIX: derivative of PID should work now as expected

## V 0.3.0
* **IQ demodulation** (simultaneous orthogonal demodulation) allows for determination of the spectroscopy signal strength. This makes one-shot optimization of the demodulation phase possible
* **Improved optimization algorithm**: Automatic optimization of the slope of a line is now more robust and converges faster
* **More accurate autolock**: Autolock reliability was improved
*  **ANALOG_OUTs** can be set using python client or GUI
* **Digital GPIO** outputs are now accessible using python client
* **Keyboard shortcuts for zoom and pan**: Use `←` / `→` / `+` / `-`
* **Device editing** is now possible, leaving device's parameters untouched
* **Extra package for python client**: `pip install linien-python-client` installs a headless version of the linien client that allows to control your lock in an environment that doesn't provide GUI libraries
* **Bug fixes and performance improvements**