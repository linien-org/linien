import numpy as np
from PyQt5 import QtGui
from linien.client.widgets import CustomWidget
from linien.client.connection import MHz, Vpp
from linien.client.utils import param2ui


class ModulationAndRampPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.modulation_frequency.setKeyboardTracking(False)
        self.ids.modulation_frequency.valueChanged.connect(self.change_modulation_frequency)
        self.ids.modulation_amplitude.setKeyboardTracking(False)
        self.ids.modulation_amplitude.valueChanged.connect(self.change_modulation_amplitude)
        self.ids.ramp_speed.currentIndexChanged.connect(self.change_ramp_speed)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        param2ui(
            params.modulation_frequency,
            self.ids.modulation_frequency,
            lambda value: value / MHz
        )
        param2ui(
            params.modulation_amplitude,
            self.ids.modulation_amplitude,
            lambda value: value / Vpp
        )
        param2ui(
            params.ramp_speed,
            self.ids.ramp_speed
        )

    def change_modulation_frequency(self):
        self.parameters.modulation_frequency.value = self.ids.modulation_frequency.value() * MHz
        self.control.write_data()

    def change_modulation_amplitude(self):
        self.parameters.modulation_amplitude.value = self.ids.modulation_amplitude.value() * Vpp
        self.control.write_data()

    def change_ramp_speed(self, decimation):
        self.parameters.ramp_speed.value = decimation
        self.control.write_data()