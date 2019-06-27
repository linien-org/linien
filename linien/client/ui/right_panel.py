from PyQt5 import QtGui
from linien.client.widgets import CustomWidget


class RightPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self):
        self.control = self.app().control
        self.parameters = self.app().parameters

        self.parameters.autolock_running.change(self.autolock_status_changed)

    def ready(self):
        self.ids.closeButton.clicked.connect(self.close_app)
        self.ids.shutdownButton.clicked.connect(self.shutdown_server)
        self.ids.openDeviceManagerButton.clicked.connect(self.open_device_manager)

    def close_app(self):
        self.app().close()

    def shutdown_server(self):
        self.app().shutdown()

    def open_device_manager(self):
        self.app().open_device_manager()

    def autolock_status_changed(self, value):
        if value:
            self.ids.settings_toolbox.setCurrentWidget(self.ids.lockingPanel)