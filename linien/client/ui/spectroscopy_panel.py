from PyQt5 import QtGui, QtWidgets
from linien.client.widgets import CustomWidget


class SpectroscopyPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.load_ui('spectroscopy_panel.ui')

    def get_param(self, name):
        return getattr(self.parameters, '%s_%s' % (name, 'a' if self.channel == 0 else 'b'))

    def ready(self):
        # FIXME: offset is disabled
        """self.ids.signal_offset.setKeyboardTracking(False)
        self.ids.signal_offset.valueChanged.connect(self.change_signal_offset)"""
        self.ids.demodulation_phase.setKeyboardTracking(False)
        self.ids.demodulation_phase.valueChanged.connect(self.change_demod_phase)
        self.ids.demodulation_frequency.currentIndexChanged.connect(self.change_demod_multiplier)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        #self.close_button.clicked.connect(self.close_app)
        #self.shutdown_button.clicked.connect(self.shutdown_server)

        self.get_param('demodulation_phase').change(
            lambda value: self.ids.demodulation_phase.setValue(value)
        )

        self.get_param('demodulation_multiplier').change(
            lambda value: self.ids.demodulation_frequency.setCurrentIndex(value - 1)
        )

        # FIXME: offset is disabled
        """self.get_param('offset').change(
            lambda value: self.ids.signal_offset.setValue(value)
        )"""

    # FIXME: offset is disabled
    """def change_signal_offset(self):
        self.get_param('offset').value = self.ids.signal_offset.value()
        self.control.write_data()"""

    def change_demod_phase(self):
        self.get_param('demodulation_phase').value = self.ids.demodulation_phase.value()
        self.control.write_data()

    def change_demod_multiplier(self, idx):
        self.get_param('demodulation_multiplier').value = idx + 1
        self.control.write_data()


class SpectroscopyChannelAPanel(SpectroscopyPanel):
    channel = 0


class SpectroscopyChannelBPanel(SpectroscopyPanel):
    channel = 1