# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0]

### Added
* Show differences when local and remote parameters do not match by @bleykauf in https://github.com/linien-org/linien/pull/400
* Show voltage on the x-axis when sweeping by @bleykauf in https://github.com/linien-org/linien/pull/404

### Changed
* Switched to Tableau color scheme and make colors consistent, i.e. signals have the same color while sweeping and when locked. By @bleykauf in https://github.com/linien-org/linien/pull/419.
* Increase upper version constraint for `importlib-metadata` by @doronbehar in https://github.com/linien-org/linien/pull/416

### Fixed

* Fixed example code in the readme by @bleykauf in https://github.com/linien-org/linien/pull/420, thanks to @Andrew-wi for reporting this issue
* Fixed a bug preventing the selection of a PSD algorithm via the GUI by @bleykauf in https://github.com/linien-org/linien/pull/421, thanks to @martinssonh for reporting this issue

## [2.0.4] - 2024-05-30

### Fixed
* Fixed bug where `*.ui` would not be included in the `linien-gui` package by @bleykauf in https://github.com/linien-org/linien/pull/407

## [2.0.3] - 2024-05-29

### Fixed
* Now compatible with Python 3.12 by bumping version of `fabric` by @bleykauf in https://github.com/linien-org/linien/pull/406, thanks to @systemofapwne for reporting this issue

### Added
* Handle corrupted json files by @bleykauf in https://github.com/linien-org/linien/pull/399

## [2.0.2] - 2024-05-14

### Fixed
* Improved performance of server CLI by @bleykauf in https://github.com/linien-org/linien/pull/396
* API token for InfluxDB is now checked by @bleykauf in https://github.com/linien-org/linien/pull/397

## [2.0.1] - 2024-05-13

### Fixed
* Fixed bug that prevented the robust autolock from working

## [2.0.0] - 2024-04-05

### Added
* Use features of Python 3.10 available on RedPitaya OS 2.0 for `linien-server` by @bleykauf in https://github.com/linien-org/linien/pull/366
* Add ability to start the server upon startup by @bleykauf in https://github.com/linien-org/linien/pull/387

### Changed
* Use systemd instead of screen for running the server by @bleykauf in https://github.com/linien-org/linien/pull/387
* Use json to store devices and parameters by @bleykauf in https://github.com/linien-org/linien/pull/357
* Better error handling by @bleykauf in https://github.com/linien-org/linien/pull/350
* Improve startup and installation process  by @bleykauf in https://github.com/linien-org/linien/pull/372
* Use official influxdb client by @bleykauf in https://github.com/linien-org/linien/pull/374
* `mdio-tools` is now included in the `linien-server` package
* Uses `rpyc==6.x` instead of `rpyc==4.x`

### Deprecated
* Removed support for RedPitaya OS 1.0: RedPitaya OS 2.0 is now necessary.

### Fixed

* Fix and enforce flake8 by @bleykauf in https://github.com/linien-org/linien/pull/368

## [1.0.2] - 2024-04-05

## Changed

* Use pypi for version check instead of `version-info.json` in the Github repository.

## [1.0.1] - 2023-12-22

## Fixed

* Fix `linien-server` startup by @bleykauf in https://github.com/linien-org/linien/pull/369

## [1.0.0] - 2023-12-01

### Added

* Add (debug) logging by @bleykauf in https://github.com/linien-org/linien/pull/349

### Changed

* Better names for autolock algorithms FastPID-only mode and PID optimizationnoise analysis by @bleykauf in https://github.com/linien-org/linien/pull/346 (fixes https://github.com/linien-org/linien/issues/235)

### Fixed

 * Fix bug where application data directory was not created by @bleykauf in https://github.com/linien-org/linien/pull/361
* Fix all kinds of dependencies issues by @doronbehar in https://github.com/linien-org/linien/pull/353

## [0.8.0] - 2023-07-06

### Added

* Add mypy configuration by @bleykauf in https://github.com/linien-org/linien/pull/336
* Add parameter logging to influxdb by @bleykauf in https://github.com/linien-org/linien/pull/311
* Adapt to RedPitaya OS 2 by @hermitdemschoenenleben in https://github.com/linien-org/linien/pull/342

### Changed
* Simplify the app structure by @bleykauf in https://github.com/linien-org/linien/pull/320
* Simplify server structure by @bleykauf in https://github.com/linien-org/linien/pull/321
* Simplify acquisition by @bleykauf in https://github.com/linien-org/linien/pull/333
* Improve installation script by @bleykauf in https://github.com/linien-org/linien/pull/335
* Improve authentication by @bleykauf in https://github.com/linien-org/linien/pull/343


## [0.7.0] - 2023-03-21

### Added

* Add ability to output slow PID on fast DACs  by @bleykauf in https://github.com/linien-org/linien/pull/312, thanks @cmf84 for the initial commit
* Add `CITATION.cff` by @bleykauf in https://github.com/linien-org/linien/pull/274

### Changed
* Use deterministic random number generation for tests by @bleykauf in https://github.com/linien-org/linien/pull/315
* Use docstrings instead of comments for parameter documentation by @bleykauf in https://github.com/linien-org/linien/pull/316

### Fixed
* README: Fix link to "getting started" by @doronbehar in https://github.com/linien-org/linien/pull/313


## [0.6.0] - 2023-02-27

### Changed

- Refactor package structure by @bleykauf in https://github.com/linien-org/linien/pull/277

### Removed
* We are no longer providing a Linux executable since it cannot be built using CI (see #263) and most users run Windows. We recommand installing linien-gui using pip (see the updated readme). If you encounter any problems, please open an issue.

## [0.5.3.post2] - 2023-02-24

### Fixed

- Fix file extension in `linien_start_server.sh`, see #291. Thank you, @doronbehar!
- Pin specific commits for installation of  `pyrp3 and `mdio-tool` in `linien_install_requirements.sh`

## [0.5.3] - 2023-04-12

### Fixed

- Fix bug preventing proper starting and stopping of linien-server

## [0.5.2] - 2023-04-05

### Added

- Better keyboard controls for spinboxes

## [0.5.1] - 2023-02-17

### Added

- Re-enable sweep for fast mode.

## [0.5.0.post1] - 2022-01-24

### Added

- **Better sweep controls** make it easier to adjust the sweep range and allow to stop the sweep altogether.
- **A new, faster PID-only mode**  allows for a higher control bandwidth by skipping modulation/demodulation steps (useful for offset locks).
- **Added Welch's method** to the measurement of the error signals power spectral density (PSD).

### Changed

* The parameters that deal with the sweep / ramp have been renamed:
    * "center" is now "sweep_center"
    * "ramp_amplitude", "ramp_speed" and * * "autolock_initial_ramp_amplitude" are now "sweep_amplitude" and * "sweep_speed" and "autolock_initial_sweep_amplitude", respectively
        There is a new boolean parameter "sweep_pause".


## [0.4.3] - 2021-06-22

### Added

- **Disabled LED blinking** as [it causes additional noise](https://github.com/RedPitaya/RedPitaya/issues/205) (thanks to Yao-Chin!)
- **DC spectroscopy signal is displayed** (thanks to aisichenko for the idea!)
- **lpsd** is now used for psd measurements (samples psd on a log scale)

### Fixed

- **various bug fixes** especially in the autolock component

## [0.4.2] - 2021-03-14

### Removed

- **Removed "Check lock" and "Watch lock" features** as they caused problems with the new autolock algorithms as well as with noise analysis. These features are planned to be reimplemented in a future release (and in a more sophisticated way). If you rely on these features, consider using Linien version `0.3.2` until then.

## [0.4.1] - 2021-03-10

### Fixed

- fix a bug in the server package that lead to an incomplete install

## [0.4.0] - 2021-03-10

### Added

- Implemented new autolock algorithms that are faster and work with high jitter
- For noise analysis, PSD of the error signal may be recorded
- Plot window of the main window may be zoomed / panned by clicking and dragging / using the mouse wheel
- Parameters are not only backed up on the client side but also on the server. When client connects to a server with parameter mismatch, the user may decide whether to keep local or remote parameters

## [0.3.2] - 2021-01-06

### Changed

- improved documentation

### Fixed

- Mark incompatibility with `rpyc==5.0.0`


## [0.3.1] - 2020-12-30

### Fixed

- derivative of PID should work now as expected

## [0.3.0] - 2020-12-23

### Added

* **IQ demodulation** (simultaneous orthogonal demodulation) allows for determination of the spectroscopy signal strength. This makes one-shot optimization of the demodulation phase possible
*  **ANALOG_OUTs** can be set using python client or GUI
* **Device editing** is now possible, leaving device's parameters untouched
* **Extra package for python client**: `pip install linien-python-client` installs a headless version of the linien client that allows to control your lock in an environment that doesn't provide GUI libraries
* **Digital GPIO** outputs are now accessible using python client
* **Keyboard shortcuts for zoom and pan**: Use `←` / `→` / `+` / `-`

### Changed

* **Improved optimization algorithm**: Automatic optimization of the slope of a line is now more robust and converges faster
* **More accurate autolock**: Autolock reliability was improved

### Fixed

* **Bug fixes and performance improvements**

[2.1.0]: https://github.com/linien-org/linien/compare/v2.0.4...v2.1.0
[2.0.4]: https://github.com/linien-org/linien/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/linien-org/linien/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/linien-org/linien/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/linien-org/linien/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/linien-org/linien/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/linien-org/linien/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/linien-org/linien/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/linien-org/linien/compare/v0.8.0...v1.0.0
[0.8.0]: https://github.com/linien-org/linien/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/linien-org/linien/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/linien-org/linien/compare/v0.3.0.post2...v0.6.0
[0.5.3.post2]: https://github.com/linien-org/linien/compare/v0.5.3...v0.5.3.post2
[0.5.3]: https://github.com/linien-org/linien/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/linien-org/linien/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/linien-org/linien/compare/v0.5.0.post1...v0.5.1
[0.5.0.post1]: https://github.com/linien-org/linien/compare/v0.4.3...v0.5.0.post1
[0.4.3]: https://github.com/linien-org/linien/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/linien-org/linien/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/linien-org/linien/compare/v0.4.0...v0.4.1
[0.3.2]: https://github.com/linien-org/linien/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/linien-org/linien/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/linien-org/linien/compare/v0.2.3...v0.3.0