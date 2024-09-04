# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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
import signal
import sys
from logging.handlers import RotatingFileHandler

import click
from linien_client.connection import LinienClient
from linien_common.communication import LinienControlService
from linien_common.config import LOG_FILE_PATH
from linien_gui import __version__
from linien_gui.config import UI_PATH, load_settings
from linien_gui.ui.device_manager import DeviceManager
from linien_gui.ui.main_window import MainWindow
from linien_gui.ui.psd_window import PSDWindow
from linien_gui.ui.version_checker import VersionCheckerThread
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from pyqtgraph.Qt import QtCore

sys.path += [str(UI_PATH)]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LinienApp(QtWidgets.QApplication):
    connection_established = pyqtSignal()

    def __init__(self, *args, **kwargs) -> None:
        super(LinienApp, self).__init__(*args, **kwargs)

        self.settings = load_settings()

        self.main_window = MainWindow()
        self.device_manager = DeviceManager()
        self.psd_window = PSDWindow()
        self.device_manager.show()

        self.aboutToQuit.connect(self.quit)

    def client_connected(self, client: LinienClient) -> None:
        self.device_manager.hide()
        self.main_window.show(client.device.host, client.device.name)

        self.client = client
        self.control: LinienControlService = client.control
        self.parameters = client.parameters

        self.connection_established.emit()

        self.periodically_check_for_changed_parameters()

        self.check_for_new_version()

    def periodically_check_for_changed_parameters(self):
        if hasattr(self, "client") and self.client and self.client.connected:
            try:
                self.parameters.check_for_changed_parameters()
            except AttributeError:
                logger.exception("check_for_changed_parameters() failed")

            QtCore.QTimer.singleShot(50, self.periodically_check_for_changed_parameters)

    def shutdown(self):
        self.client.control.exposed_shutdown()
        self.quit()

    def open_psd_window(self):
        # first hiding it, then showing it brings it to foregroud if it is in background
        self.psd_window.hide()
        self.psd_window.show()

    def open_device_manager(self):
        self.main_window.hide()
        self.device_manager.show()

        self.client.disconnect()
        del self.client

    def close_all_secondary_windows(self):
        self.psd_window.hide()

    def check_for_new_version(self):
        self.version_checker = VersionCheckerThread()
        self.version_checker.check_done.connect(self.new_version_available)
        self.version_checker.start()

    def new_version_available(self, new_version_available):
        if new_version_available:
            logger.info("New version available")
            self.main_window.show_new_version_available()
        else:
            logger.info("No new version available")
            QtCore.QTimer.singleShot(1000 * 60 * 60, self.check_for_new_version)


# ignore type, otherwise "Argument 1 has incompatible type "Callable[[int, bool, str |
# None, bool], Any]"; expected <nothing>" is raised for click 8.1.4.
@click.command("linien")  # type: ignore[arg-type]
@click.version_option(__version__)
def main():

    file_handler = RotatingFileHandler(
        str(LOG_FILE_PATH), maxBytes=1000000, backupCount=10
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter("%(name)-30s %(levelname)-8s %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    app = LinienApp(sys.argv)
    logger.info("Starting Linien GUI")

    # catch ctrl-c and shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
