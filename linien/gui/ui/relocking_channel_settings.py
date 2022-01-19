from PyQt5 import QtWidgets

from linien.gui.utils_gui import param2ui
from linien.gui.widgets import CustomWidget


class RelockingChannelSettings(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.load_ui("relocking_channel_settings.ui")

    def ready(self):
        self.ids.enableRelockingThisChannel.stateChanged.connect(
            self.relock_enabled_state_changed
        )
        self.ids.relockingThisChannelMin.setKeyboardTracking(False)
        self.ids.relockingThisChannelMin.valueChanged.connect(self.min_value_changed)
        self.ids.relockingThisChannelMax.setKeyboardTracking(False)
        self.ids.relockingThisChannelMax.valueChanged.connect(self.max_value_changed)

    @property
    def signal_name(self):
        raise NotImplementedError()

    @property
    def parameter_enabled(self):
        return getattr(
            self.parameters, "automatic_relocking_%s_enabled" % self.signal_name
        )

    @property
    def parameter_min(self):
        return getattr(self.parameters, "automatic_relocking_%s_min" % self.signal_name)

    @property
    def parameter_max(self):
        return getattr(self.parameters, "automatic_relocking_%s_max" % self.signal_name)

    def connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.parameter_min, self.ids.enableRelockingThisChannel)
        param2ui(self.parameter_max, self.ids.enableRelockingThisChannel)

        def enable_or_disable_relocking_panel(enable):
            self.ids.relockBasedOnValuePanel.setEnabled(enable)

        self.parameter_enabled.on_change(enable_or_disable_relocking_panel)

    def relock_enabled_state_changed(self):
        self.parameter_enabled.value = int(
            self.ids.enableRelockingThisChannel.checkState()
        )
        self.control.write_registers()

    def min_value_changed(self):
        self.parameter_min.value = self.ids.relockingThisChannelMin.value()
        self.control.write_registers()

    def max_value_changed(self):
        self.parameter_max.value = self.ids.relockingThisChannelMax.value()
        self.control.write_registers()


class RelockingControlChannelSettings(RelockingChannelSettings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def signal_name(self):
        return "control"


class RelockingErrorChannelSettings(RelockingChannelSettings):
    @property
    def signal_name(self):
        return "error"


class RelockingMonitorChannelSettings(RelockingChannelSettings):
    @property
    def signal_name(self):
        return "monitor"
