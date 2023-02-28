## V 0.6.0
- Refactor package structure by @bleykauf in https://github.com/linien-org/linien/pull/277

## V 0.5.3.post2
- Pin specific commits for installation of  `pyrp3 and `mdio-tool` in `linien_install_requirements.sh`
- Fix file extension in `linien_start_server.sh`, see #291. Thank you, @doronbehar!
- Bump future from 0.18.2 to 0.18.3 by @dependabot in https://github.com/linien-org/linien/pull/305

## V 0.5.3
- Fix bug preventing proper starting and stopping of linien-server

## V 0.5.2
- Better keyboard controls for spinboxes

## V 0.5.1
- Re-enable sweep for fast mode.

## V 0.5.0
- **Better sweep controls** make it easier to adjust the sweep range and allow to stop the sweep altogether.
- **A new, faster PID-only mode**  allows for a higher control bandwidth by skipping modulation/demodulation steps (useful for offset locks).
- **Added Welch's method** to the measurement of the error signals power spectral density (PSD).

## V 0.4.3
- **Disabled LED blinking** as [it causes additional noise](https://github.com/RedPitaya/RedPitaya/issues/205) (thanks to Yao-Chin!)
- **DC spectroscopy signal is displayed** (thanks to aisichenko for the idea!)
- **lpsd** is now used for psd measurements (samples psd on a log scale)
- **various bug fixes** especially in the autolock component

## V 0.4.2
- **Removed "Check lock" and "Watch lock" features** as they caused problems with the new autolock algorithms as well as with noise analysis. These features are planned to be reimplemented in a future release (and in a more sophisticated way). If you rely on these features, consider using Linien version `0.3.2` until then.

## V 0.4.1
- fix a bug in the server package that lead to an incomplete install

## V 0.4.0
- Implemented new autolock algorithms that are faster and work with high jitter
- For noise analysis, PSD of the error signal may be recorded
- Plot window of the main window may be zoomed / panned by clicking and dragging / using the mouse wheel
- Parameters are not only backed up on the client side but also on the server. When client connects to a server with parameter mismatch, the user may decide whether to keep local or remote parameters

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