import numpy as np
from PyQt5 import QtGui
from spectrolock.client.widgets import CustomWidget

MHz = 0x10000000 / 8
Vpp = 0xffff / 2

class SpectroscopyPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self, app):
        self.app = app
        params = app.parameters
        self.parameters = params

        #self.close_button.clicked.connect(self.close_app)
        #self.shutdown_button.clicked.connect(self.shutdown_server)

        params.modulation_frequency.change(
            lambda value: self.ids.modulation_frequency.setValue(value / MHz)
        )

        params.modulation_amplitude.change(
            lambda value: self.ids.modulation_amplitude.setValue(value / Vpp)
        )

        params.ramp_speed.change(
            lambda value: self.ids.ramp_speed.setValue(value)
        )

        params.demodulation_phase.change(
            lambda value: self.ids.demodulation_phase.setValue(value)
        )

        params.offset.change(
            lambda value: self.ids.signal_offset.setValue(value)
        )

        params.offset.change(
            lambda value: self.ids.signal_offset.setValue(value)
        )

        self.ids.modulation_frequency.valueChanged.connect(self.change_modulation_frequency)
        self.ids.modulation_amplitude.valueChanged.connect(self.change_modulation_amplitude)
        self.ids.signal_offset.valueChanged.connect(self.change_signal_offset)

    def change_modulation_frequency(self):
        self.parameters.modulation_frequency.value = self.ids.modulation_frequency.value() * MHz

    def change_modulation_amplitude(self):
        self.parameters.modulation_amplitude.value = self.ids.modulation_amplitude.value() * Vpp

    def change_signal_offset(self):
        self.parameters.offset.value = self.ids.signal_offset.value()
        self.control.write_data()