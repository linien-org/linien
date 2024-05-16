# Copyright 2024 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

import logging

from linien_gui.config import UI_PATH
from linien_gui.utils import get_linien_app_instance
from PyQt5 import QtWidgets, uic

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RelockingPanel(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs) -> None:
        super(RelockingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "relocking_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

    def on_connection_established(self) -> None:
        self.parameters = self.app.parameters
        self.control = self.app.control
