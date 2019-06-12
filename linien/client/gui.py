import os
import sys
import numpy as np

from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtCore, QtGui
# add ui folder to path
sys.path += [
    os.path.join(*list(
        os.path.split(os.path.abspath(__file__))[:-1]) + ['ui']
    )
]

from linien.client.widgets import CustomWidget
from linien.client.ui.main_window import Ui_MainWindow
from linien.client.ui.device_manager import Ui_DeviceManager


class QTApp(QtCore.QObject):
    ready = QtCore.pyqtSignal(bool)

    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)

        self.main_window = QtWidgets.QMainWindow()
        self.main_window.app = self
        ui = Ui_MainWindow()
        ui.setupUi(self.main_window)

        self.device_manager = QtWidgets.QMainWindow()
        self.device_manager.app = self
        ui2 = Ui_DeviceManager()
        ui2.setupUi(self.device_manager)
        self.device_manager.show()

        self.app.aboutToQuit.connect(lambda: self.app.quit())

        super().__init__()

    def connected(self, connection, parameters, control):
        self.device_manager.hide()
        self.main_window.show()

        self.connection = connection
        self.control = control
        self.parameters = parameters

        self.ready.connect(self.init)
        self.ready.emit(True)

    def init(self):
        for instance in CustomWidget.instances:
            instance.connection_established()

        self.parameters.call_listeners()

    def get_widget(self, name, window=None):
        """Queries a widget by name."""
        window = window or self.main_window
        return window.findChild(QtCore.QObject, name)

    def close(self):
        self.app.quit()

    def shutdown(self):
        self.control.shutdown()
        self.close()

    def open_device_manager(self):
        self.main_window.hide()
        self.device_manager.show()

        self.connection.disconnect()
        del self.connection