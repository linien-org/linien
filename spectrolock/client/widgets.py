import weakref
from pyqtgraph.Qt import QtCore, QtGui


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

    def connection_established(self, app):
        pass

    def get_widget(self, name):
        """Queries a widget by name."""
        return self.findChild(QtCore.QObject, name)