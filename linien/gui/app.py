import os
import signal
import sys

from plumbum import colors
from traceback import print_exc

from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtCore, QtGui


# it may seem odd to include '.', but for some reason this is needed for
# standalone windows executable
sys.path += ["../", os.path.join("..", ".."), "."]

import linien
from linien.gui.widgets import CustomWidget, ui_path

sys.path += [ui_path]

from linien.gui.ui.device_manager import DeviceManager
from linien.gui.ui.version_checker import VersionCheckerThread
from linien.gui.ui.main_window import MainWindow
from linien.gui.ui.psd_window import PSDWindow
from linien.gui.utils_gui import set_window_icon


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

        self.psd_window = PSDWindow()
        self.psd_window.app = self

        self.app.aboutToQuit.connect(lambda: self.app.quit())

        super().__init__()

    def connected(self, connection, parameters, control):
        self.device_manager.hide()
        self.main_window.show(connection.host, connection.device["name"])

        self.connection = connection
        self.control = control
        self.parameters = parameters

        self.ready.connect(self.init)
        self.ready.emit(True)

    def init(self):
        for instance in CustomWidget.instances:
            try:
                instance.connection_established()
            except:
                print(
                    "the error below happend when calling connection_established of a widget. This may happen if the widget was recently destroyed."
                )
                print_exc()

        self.call_listeners()

        self.check_for_new_version()

    def call_listeners(self):
        if (
            hasattr(self, "connection")
            and self.connection
            and self.connection.connected
        ):
            try:
                self.parameters.call_listeners()
            except:
                print(colors.red | "call_listeners() failed")
                print_exc()

            QtCore.QTimer.singleShot(50, self.call_listeners)

    def get_widget(self, name, window=None):
        """Queries a widget by name."""
        window = window or self.main_window
        return window.findChild(QtCore.QObject, name)

    def close(self):
        self.app.quit()

    def shutdown(self):
        self.control.shutdown()
        self.close()

    def open_psd_window(self):
        # first hiding it, then showing it brings it to foregroud if it is in
        # background
        self.psd_window.hide()
        self.psd_window.show()

    def open_device_manager(self):
        self.main_window.hide()
        self.device_manager.show()

        self.connection.disconnect()
        del self.connection

    def close_all_secondary_windows(self):
        self.psd_window.hide()

    def check_for_new_version(self):
        self.version_checker = VersionCheckerThread()
        self.version_checker.check_done.connect(self.new_version_available)
        self.version_checker.start()

    def new_version_available(self, new_version_available):
        if new_version_available:
            print("new version available")
            self.main_window.show_new_version_available()
        else:
            print("no new version available")
            QtCore.QTimer.singleShot(1000 * 60 * 60, self.check_for_new_version)


def run_application():
    print("Linien spectroscopy lock version " + (colors.bold | linien.__version__))
    gui = QTApp()

    # catch ctrl-c and shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(gui.app.exec_())


if __name__ == "__main__":
    run_application()
