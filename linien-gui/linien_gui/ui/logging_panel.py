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

from linien_client.remote_parameters import RemoteParameter
from linien_gui.widgets import CustomWidget
from PyQt5 import QtWidgets


class LoggingPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("logging_panel.ui")

    def ready(self):
        self.ids.logParametersToolButton.setPopupMode(
            QtWidgets.QToolButton.InstantPopup
        )

    def connection_established(self):
        self.parameters = self.app.parameters
        self.logged_parameters_menu = LoggedParametersMenu()
        self.logged_parameters_menu.create_menu_entries(self.parameters)
        self.ids.logParametersToolButton.setMenu(self.logged_parameters_menu)


# checkable menu for logged parameters, inspired by
# https://stackoverflow.com/a/22775990/2750945
class LoggedParametersToolButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        super(LoggedParametersToolButton, self).__init__()


class LoggedParametersMenu(QtWidgets.QMenu):
    def __init__(self, *args, **kwargs):
        super(LoggedParametersMenu, self).__init__()

    def create_menu_entries(self, parameters):
        params = [p for p in dir(parameters) if not p.startswith("_")]
        for p_name in params:
            p = getattr(parameters, p_name)
            if isinstance(p, RemoteParameter):
                if p.loggable:
                    action = QtWidgets.QAction(p_name, self, checkable=True)
                    action = self.addAction(action)
