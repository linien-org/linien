import os
import sys
import numpy as np

from PyQt5 import QtWidgets
from plumbum import colors
from traceback import print_exc
from pyqtgraph.Qt import QtCore, QtGui
# add ui folder to path
ui_path = os.path.join(*list(
    os.path.split(os.path.abspath(__file__))[:-1]) + ['ui']
)
sys.path += [ui_path]

from linien.client.widgets import CustomWidget
from linien.client.ui.main_window import MainWindow
from linien.client.ui.device_manager import DeviceManager
from linien.client.utils_gui import set_window_icon


class QTApp(QtCore.QObject):
    ready = QtCore.pyqtSignal(bool)

    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)

        self.main_window = MainWindow()
        self.main_window.app = self
        set_window_icon(self.main_window)

        self.device_manager = DeviceManager()
        self.device_manager.app = self
        self.device_manager.show()

        self.app.aboutToQuit.connect(lambda: self.app.quit())


        super().__init__()

    def connected(self, connection, parameters, control):
        self.device_manager.hide()
        self.main_window.show(connection.host, connection.device['name'])

        self.connection = connection
        self.control = control
        self.parameters = parameters

        self.ready.connect(self.init)
        self.ready.emit(True)

    def init(self):
        for instance in CustomWidget.instances:
            instance.connection_established()

        self.call_listeners()

    def call_listeners(self):
        if hasattr(self, 'connection') and self.connection and self.connection.connected:
            try:
                self.parameters.call_listeners()
            except:
                print(colors.red | 'call_listeners() failed')
                print_exc()

            QtCore.QTimer.singleShot(100, self.call_listeners)

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