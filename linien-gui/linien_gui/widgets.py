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

import weakref
from pathlib import Path

from PyQt5 import uic
from pyqtgraph.Qt import QtCore

UI_PATH = Path(__file__).parents[0].resolve() / "ui"


class IDSelector:
    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, name):
        return self.parent.get_widget(name)


class CustomWidget:
    instances = []

    def __init__(self, *args, **kwargs):
        self.__class__.instances.append(weakref.proxy(self))

        super().__init__(*args, **kwargs)

        self.ids = IDSelector(self)

        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        pass

    def connection_established(self):
        # This is executed the client succesfully established a connection to the server
        # and can be extended by inheritting classes.
        pass

    def get_widget(self, name):
        """Queries a widget by name."""
        return self.findChild(QtCore.QObject, name)

    @property
    def app(self):
        # this property is set manually. Probably there is a more elegant way
        # to solve this...
        return self.window()._app

    @app.setter
    def app(self, app):
        self._app = app

    def load_ui(self, name):
        assert name.endswith(".ui")
        path = UI_PATH / name
        uic.loadUi(str(path), self)
