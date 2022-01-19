from urllib.request import urlopen

from PyQt5.QtCore import QThread, pyqtSignal

import linien


def version_string_to_tuple(version):
    parts = tuple(int(v) for v in version.split("."))
    assert len(parts) == 3
    return parts


class VersionCheckerThread(QThread):
    check_done = pyqtSignal(bool)

    def run(self):
        new_version_available = False
        print("check whether new version is available")
        try:
            with urlopen(
                "https://raw.githubusercontent.com/hermitdemschoenenleben/linien/master/latest_version"  # noqa: E501
            ) as response:
                response_content = response.read().decode().strip()
                latest_version = version_string_to_tuple(response_content)
                our_version = version_string_to_tuple(linien.__version__)
                new_version_available = latest_version > our_version

        except Exception:
            pass

        self.check_done.emit(new_version_available)
