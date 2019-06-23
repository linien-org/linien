import weakref
from os import path
from PyQt5 import uic
from pyqtgraph.Qt import QtCore, QtGui
from linien.client.gui import ui_path


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
        pass

    def get_widget(self, name):
        """Queries a widget by name."""
        return self.findChild(QtCore.QObject, name)

    def app(self):
        # this property is set manually. Probably there is a more elegant way
        # to solve this...
        return self.window().app

    def load_ui(self, name):
        assert name.endswith('.ui')
        uic.loadUi(path.join(ui_path, name), self)