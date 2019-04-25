from PyQt5 import QtGui
from spectrolock.client.widgets import CustomWidget


class RightPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self, app):
        self.app = app

        self.ids.closeButton.clicked.connect(self.close_app)
        self.ids.shutdownButton.clicked.connect(self.shutdown_server)

    def close_app(self):
        self.app.close()

    def shutdown_server(self):
        self.app.shutdown()