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
from linien_gui.widgets import UI_PATH
from PyQt5 import QtWidgets, uic


class LoggingPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "logging_panel.ui", self)
        self.app = QtWidgets.QApplication.instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.logParametersToolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.logged_parameters_menu = LoggedParametersMenu()

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.logged_parameters_menu.create_menu_entries(self.parameters)
        self.logParametersToolButton.setMenu(self.logged_parameters_menu)


# checkable menu for logged parameters, inspired by
# https://stackoverflow.com/a/22775990/2750945
class LoggedParametersToolButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        super(LoggedParametersToolButton, self).__init__()


class LoggedParametersMenu(QtWidgets.QMenu):
    def __init__(self, *args, **kwargs):
        super(LoggedParametersMenu, self).__init__()
        self.triggered.connect(self.on_action_clicked)

    def create_menu_entries(self, parameters: RemoteParameters):
        for name, param in parameters:
            if param.loggable:
                action = QtWidgets.QAction(name, parent=self, checkable=True)  # type: ignore[call-overload] # noqa: E501
                # action.setChecked(param.log)
                self.addAction(action)

    def on_action_clicked(self, action: QtWidgets.QAction):
        param = action.text()
        if action.isChecked():
            print("Turn on logging for ", param)
        else:
            print("Turn off logging for ", param)
