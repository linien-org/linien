from PyQt5 import QtGui
from linie.client.widgets import CustomWidget


class RightPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self):
        pass

    def close_app(self):
        self.app().close()

    def shutdown_server(self):
        self.app().shutdown()

    def open_device_manager(self):
        self.app().open_device_manager()

    def start_manual_lock(self):
        # FIXME: missing
        pass