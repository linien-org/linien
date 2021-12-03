from PyQt5 import QtWidgets

from linien.client.connection import MHz, Vpp
from linien.gui.utils_gui import param2ui
from linien.gui.widgets import CustomWidget


class ModulationAndRampPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("modulation_ramp_panel.ui")

    def ready(self):
        self.ids.modulation_frequency.setKeyboardTracking(False)
        self.ids.modulation_frequency.valueChanged.connect(
            self.change_modulation_frequency
        )
        self.ids.modulation_amplitude.setKeyboardTracking(False)
        self.ids.modulation_amplitude.valueChanged.connect(
            self.change_modulation_amplitude
        )
        self.ids.ramp_speed.currentIndexChanged.connect(self.change_ramp_speed)

        self.ids.spectroscopyTabs.setCurrentIndex(0)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        param2ui(
            params.modulation_frequency,
            self.ids.modulation_frequency,
            lambda value: value / MHz,
        )
        param2ui(
            params.modulation_amplitude,
            self.ids.modulation_amplitude,
            lambda value: value / Vpp,
        )
        param2ui(params.ramp_speed, self.ids.ramp_speed)

        params.dual_channel.on_change(self.dual_channel_changed)

        def fast_mode_changed(fast_mode_enabled):
            """Disables controls that are irrelevant if fast mode is enabled"""
            widgets_to_disable = (
                self.ids.modulation_frequency_group,
                self.ids.modulation_amplitude_group,
                self.ids.spectroscopyTabs,
            )
            for widget in widgets_to_disable:
                widget.setEnabled(not fast_mode_enabled)

        params.fast_mode.on_change(fast_mode_changed)

    def change_modulation_frequency(self):
        self.parameters.modulation_frequency.value = (
            self.ids.modulation_frequency.value() * MHz
        )
        self.control.write_data()

    def change_modulation_amplitude(self):
        self.parameters.modulation_amplitude.value = (
            self.ids.modulation_amplitude.value() * Vpp
        )
        self.control.write_data()

    def change_ramp_speed(self, decimation):
        self.parameters.ramp_speed.value = decimation
        self.control.write_data()

    def dual_channel_changed(self, value):
        self.ids.spectroscopyBPanel.setEnabled(value)
        self.ids.spectroscopyBPanelDisabled.setVisible(not value)
