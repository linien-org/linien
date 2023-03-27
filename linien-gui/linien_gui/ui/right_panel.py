# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5 import QtCore, QtWidgets


class RightPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        self.app = self.window().app
        self.app.connection_established.connect(self.on_connection_established)
        self.main_window = self.window()
        self.main_window.closeButton.clicked.connect(self.close_app)
        self.main_window.shutdownButton.clicked.connect(self.shutdown_server)
        self.main_window.openDeviceManagerButton.clicked.connect(
            self.open_device_manager
        )
        self.main_window.pid_parameter_optimization_button.clicked.connect(
            self.open_psd_window
        )

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        self.parameters.autolock_running.on_change(self.autolock_status_changed)
        self.parameters.optimization_running.on_change(self.optimization_status_changed)
        self.parameters.lock.on_change(self.enable_or_disable_panels)

        def highlight_psd_button(locked):
            self.main_window.pid_parameter_optimization_button.setStyleSheet(
                "background: #00aa00;" if locked else ""
            )

        self.parameters.lock.on_change(highlight_psd_button)

    def close_app(self):
        self.app.close()

    def shutdown_server(self):
        self.app.shutdown()

    def open_psd_window(self):
        self.app.open_psd_window()

    def open_device_manager(self):
        self.app.open_device_manager()

    def autolock_status_changed(self, value):
        if value:
            self.settings_toolbox.setCurrentWidget(self.lockingPanel)

        self.enable_or_disable_panels()

    def optimization_status_changed(self, value):
        if value:
            self.settings_toolbox.setCurrentWidget(self.optimizationPanel)

        self.enable_or_disable_panels()

    def enable_or_disable_panels(self, *args):
        lock = self.parameters.lock.value
        autolock = self.parameters.autolock_running.value
        optimization = self.parameters.optimization_running.value

        def enable_panels(panel_names, condition):
            for panel_name in panel_names:
                getattr(self.main_window, panel_name).setEnabled(condition)

        enable_panels(("generalPanel",), not autolock and not optimization and not lock)
        enable_panels(
            ("modSpectroscopyPanel", "viewPanel", "lockingPanel"), not optimization
        )
        enable_panels(("optimizationPanel",), not autolock and not lock)
