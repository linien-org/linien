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

from PyQt5 import QtWidgets

from linien.gui.widgets import CustomWidget


class LoggingPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("logging_panel.ui")

    def ready(self):
        logged_parameters_menu = LoggedParametersMenu()
        self.ids.logParametersToolButton.setMenu(logged_parameters_menu)
        self.ids.logParametersToolButton.setPopupMode(
            QtWidgets.QToolButton.InstantPopup
        )


# checkable menu for logged parameters, inspired by
# https://stackoverflow.com/a/22775990/2750945
class LoggedParametersToolButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        super(LoggedParametersToolButton, self).__init__()


class LoggedParametersMenu(QtWidgets.QMenu):
    def __init__(self, *args, **kwargs):
        super(LoggedParametersMenu, self).__init__()
        for i in range(20):
            action = QtWidgets.QAction("Parameter {}".format(i), self, checkable=True)
            action = self.addAction(action)
