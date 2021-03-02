from PyQt5 import QtGui
from linien.gui.widgets import CustomWidget


class RightPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self):
        self.control = self.app().control
        self.parameters = self.app().parameters

        self.parameters.autolock_running.on_change(self.autolock_status_changed)
        self.parameters.optimization_running.on_change(self.optimization_status_changed)
        self.parameters.lock.on_change(self.enable_or_disable_panels)

        def highlight_psd_button(locked):
            self.ids.pid_parameter_optimization_button.setStyleSheet(
                "background: #00aa00;" if locked else ""
            )

        self.parameters.lock.on_change(highlight_psd_button)

    def ready(self):
        self.ids.closeButton.clicked.connect(self.close_app)
        self.ids.shutdownButton.clicked.connect(self.shutdown_server)
        self.ids.openDeviceManagerButton.clicked.connect(self.open_device_manager)
        self.ids.pid_parameter_optimization_button.clicked.connect(self.open_psd_window)

    def close_app(self):
        self.app().close()

    def shutdown_server(self):
        self.app().shutdown()

    def open_psd_window(self):
        self.app().open_psd_window()

    def open_device_manager(self):
        self.app().open_device_manager()

    def autolock_status_changed(self, value):
        if value:
            self.ids.settings_toolbox.setCurrentWidget(self.ids.lockingPanel)

        self.enable_or_disable_panels()

    def optimization_status_changed(self, value):
        if value:
            self.ids.settings_toolbox.setCurrentWidget(self.ids.optimizationPanel)

        self.enable_or_disable_panels()

    def enable_or_disable_panels(self, *args):
        lock = self.parameters.lock.value
        autolock = self.parameters.autolock_running.value
        optimization = self.parameters.optimization_running.value

        def enable_panels(panel_names, condition):
            for panel_name in panel_names:
                getattr(self.ids, panel_name).setEnabled(condition)

        enable_panels(("generalPanel",), not autolock and not optimization and not lock)
        enable_panels(
            ("modSpectroscopyPanel", "viewPanel", "lockingPanel"), not optimization
        )
        enable_panels(("optimizationPanel",), not autolock and not lock)
