from urllib.request import urlopen

from packaging import version
from PyQt5.QtCore import QThread, pyqtSignal

import linien


class VersionCheckerThread(QThread):
    check_done = pyqtSignal(bool)

    def run(self):
        new_version_available = False
        print("Check whether new version is available.")
        try:
            with urlopen(
                "https://raw.githubusercontent.com/hermitdemschoenenleben/linien/master/latest_version"  # noqa: E501
            ) as response:
                response_content = response.read().decode().strip()
                latest_version = version.parse(response_content)
                our_version = version.parse(linien.__version__)
                new_version_available = latest_version > our_version
        finally:
            self.check_done.emit(new_version_available)
