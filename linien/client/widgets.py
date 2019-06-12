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

    def bar(self):
        print('foo')