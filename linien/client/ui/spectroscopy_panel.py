from PyQt5 import QtGui, QtWidgets
from linien.client.widgets import CustomWidget


class SpectroscopyPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.load_ui('spectroscopy_panel.ui')

    def ready(self):
        self.ids.signal_offset.editingFinished.connect(self.change_signal_offset)
        self.ids.demodulation_phase.editingFinished.connect(self.change_demod_phase)
        self.ids.demodulation_frequency.currentIndexChanged.connect(self.change_demod_multiplier)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        #self.close_button.clicked.connect(self.close_app)
        #self.shutdown_button.clicked.connect(self.shutdown_server)

        params.demodulation_phase.change(
            lambda value: self.ids.demodulation_phase.setValue(value)
        )

        params.demodulation_multiplier.change(
            lambda value: self.ids.demodulation_frequency.setCurrentIndex(value - 1)
        )

        params.offset.change(
            lambda value: self.ids.signal_offset.setValue(value)
        )

    def change_signal_offset(self):
        self.parameters.offset.value = self.ids.signal_offset.value()
        self.control.write_data()

    def change_demod_phase(self):
        self.parameters.demodulation_phase.value = self.ids.demodulation_phase.value()
        self.control.write_data()

    def change_demod_multiplier(self, idx):
        self.parameters.demodulation_multiplier.value = idx + 1
        self.control.write_data()
