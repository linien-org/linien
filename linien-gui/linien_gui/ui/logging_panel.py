# Copyright 2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien.
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

from linien_client.remote_parameters import RemoteParameters
from linien_common.influxdb import InfluxDBCredentials
from linien_gui.utils import get_linien_app_instance
from linien_gui.widgets import UI_PATH
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal


class LoggingPanel(QtWidgets.QWidget):
    set_parameter_log = pyqtSignal(str, bool)

    logParametersToolButton: "LoggedParametersToolButton"
    lineEditURL: QtWidgets.QLineEdit
    lineEditOrg: QtWidgets.QLineEdit
    lineEditToken: QtWidgets.QLineEdit
    lineEditBucket: QtWidgets.QLineEdit
    lineEditMeas: QtWidgets.QLineEdit
    influxUpdateButton: QtWidgets.QPushButton
    influxTestIndicator: QtWidgets.QLabel
    logIntervalSpinBox: QtWidgets.QSpinBox
    logPushButton: QtWidgets.QPushButton

    def __init__(self, *args, **kwargs) -> None:
        super(LoggingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "logging_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.logParametersToolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.loggedParametersMenu = LoggedParametersMenu()

    def on_connection_established(self) -> None:
        self.parameters = self.app.parameters
        self.control = self.app.control

        self.loggedParametersMenu.create_menu_entries(self.parameters)
        self.logParametersToolButton.setMenu(self.loggedParametersMenu)

        self.loggedParametersMenu.item_clicked.connect(
            self.on_parameter_log_status_changed
        )
        self.logPushButton.clicked.connect(self.on_logging_button_clicked)
        self.influxUpdateButton.clicked.connect(self.on_influx_update_button_clicked)

    def on_parameter_log_status_changed(self, param_name: str, status: bool) -> None:
        self.control.exposed_set_parameter_log(param_name, status)

    def on_logging_button_clicked(self) -> None:
        if self.logPushButton.isChecked():
            self.control.exposed_start_logging(self.logIntervalSpinBox.value())
            self.logPushButton.setText("Stop Logging")
            self.logIntervalSpinBox.setEnabled(False)
        else:
            self.control.exposed_stop_logging()
            self.logPushButton.setText("Stop Logging")
            self.logIntervalSpinBox.setEnabled(True)

    def on_influx_update_button_clicked(self) -> None:
        print("Updating influxdb credentials")
        credentials = InfluxDBCredentials(
            url=self.lineEditURL.text(),
            org=self.lineEditOrg.text(),
            token=self.lineEditToken.text(),
            bucket=self.lineEditBucket.text(),
            measurement=self.lineEditMeas.text(),
        )
        self.control.exposed_update_influxdb_credentials(credentials)


# checkable menu for logged parameters, inspired by
# https://stackoverflow.com/a/22775990/2750945
class LoggedParametersToolButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        super(LoggedParametersToolButton, self).__init__(*args, **kwargs)


class LoggedParametersMenu(QtWidgets.QMenu):
    item_clicked = pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs) -> None:
        super(LoggedParametersMenu, self).__init__(*args, **kwargs)

    def create_menu_entries(self, parameters: RemoteParameters) -> None:
        for name, param in parameters:
            if param.loggable:
                action = QtWidgets.QAction(name, parent=self, checkable=True)  # type: ignore[call-overload] # noqa: E501
                action.setChecked(param.log)
                self.addAction(action)
        self.triggered.connect(self.on_item_selected)

    def on_item_selected(self, action: QtWidgets.QAction) -> None:
        param_name = action.text()
        self.item_clicked.emit(param_name, action.isChecked())
