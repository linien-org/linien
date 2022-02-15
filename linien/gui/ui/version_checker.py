import json
from urllib.error import HTTPError
from urllib.request import urlopen

from packaging import version
from PyQt5.QtCore import QThread, pyqtSignal

import linien


class VersionCheckerThread(QThread):
    check_done = pyqtSignal(bool)

    def run(self):
        our_version = version.parse(linien.__version__)
        latest_version = our_version
        print("Check whether new version is available.")
        url_legacy = "https://raw.githubusercontent.com/hermitdemschoenenleben/linien/master/version-info.json"  # noqa: E501
        url = "https://raw.githubusercontent.com/linien-org/linien/master/version-info.json"  # noqa: E501
        try:
            with urlopen(url_legacy) as response:
                response_content = json.loads(response.read())
                latest_version = version.parse(response_content["latest"])
        except HTTPError:
            # after repo is moved to new location
            with urlopen(url) as response:
                response_content = json.loads(response.read())
                latest_version = version.parse(response_content["latest"])
        finally:
            self.check_done.emit(latest_version > our_version)
