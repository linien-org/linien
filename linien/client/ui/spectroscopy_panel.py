from PyQt5 import QtGui, QtWidgets
from linien.common import LOW_PASS_FILTER, HIGH_PASS_FILTER
from linien.client.widgets import CustomWidget
from linien.client.utils import param2ui


class SpectroscopyPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.load_ui('spectroscopy_panel.ui')

    def get_param(self, name):
        return getattr(self.parameters, '%s_%s' % (name, 'a' if self.channel == 0 else 'b'))

    def ready(self):
        self.ids.signal_offset.setKeyboardTracking(False)
        self.ids.signal_offset.valueChanged.connect(self.change_signal_offset)
        self.ids.demodulation_phase.setKeyboardTracking(False)
        self.ids.demodulation_phase.valueChanged.connect(self.change_demod_phase)
        self.ids.demodulation_frequency.currentIndexChanged.connect(self.change_demod_multiplier)
        self.ids.filter_enabled.stateChanged.connect(self.change_filter_enabled)
        self.ids.filter_frequency.valueChanged.connect(self.change_filter_frequency)
        self.ids.filter_type.currentIndexChanged.connect(self.change_filter_type)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        #self.close_button.clicked.connect(self.close_app)
        #self.shutdown_button.clicked.connect(self.shutdown_server)

        param2ui(
            self.get_param('demodulation_phase'),
            self.ids.demodulation_phase
        )
        param2ui(
            self.get_param('demodulation_multiplier'),
            self.ids.demodulation_frequency,
            lambda value: value - 1
        )
        param2ui(
            self.get_param('offset'),
            self.ids.signal_offset
        )
        param2ui(self.get_param('filter_enabled'), self.ids.filter_enabled)
        param2ui(
            self.get_param('filter_frequency'),
            self.ids.filter_frequency
        )
        param2ui(
            self.get_param('filter_type'),
            self.ids.filter_type,
            lambda type_: {
                LOW_PASS_FILTER: 0,
                HIGH_PASS_FILTER: 1
            }[type_]
        )

    def change_signal_offset(self):
        self.get_param('offset').value = self.ids.signal_offset.value()
        self.control.write_data()

    def change_demod_phase(self):
        self.get_param('demodulation_phase').value = self.ids.demodulation_phase.value()
        self.control.write_data()

    def change_demod_multiplier(self, idx):
        self.get_param('demodulation_multiplier').value = idx + 1
        self.control.write_data()

    def change_filter_frequency(self):
        self.get_param('filter_frequency').value = self.ids.filter_frequency.value()
        self.control.write_data()

    def change_filter_enabled(self):
        filter_enabled = int(self.ids.filter_enabled.checkState() > 0)
        self.get_param('filter_enabled').value = filter_enabled
        self.control.write_data()

    def change_filter_type(self, *args):
        param = self.get_param('filter_type')
        param.value = (LOW_PASS_FILTER, HIGH_PASS_FILTER) \
                        [self.ids.filter_type.currentIndex()]
        self.control.write_data()


class SpectroscopyChannelAPanel(SpectroscopyPanel):
    channel = 0


class SpectroscopyChannelBPanel(SpectroscopyPanel):
    channel = 1