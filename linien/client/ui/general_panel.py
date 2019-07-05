import numpy as np
from PyQt5 import QtGui

from linien.common import convert_channel_mixing_value
from linien.client.utils import param2ui
from linien.client.widgets import CustomWidget
from linien.client.connection import MHz, Vpp


class GeneralPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.rampOnSlow.stateChanged.connect(self.ramp_on_slow_changed)
        self.ids.channel_mixing_slider.valueChanged.connect(self.channel_mixing_changed)
        self.ids.dual_channel.stateChanged.connect(self.dual_channel_changed)
        self.ids.enable_slow_out.stateChanged.connect(self.enable_slow_changed)
        self.ids.slow_polarity.currentIndexChanged.connect(self.change_slow_polarity)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        param2ui(params.ramp_on_slow, self.ids.rampOnSlow)
        def ramp_on_slow_param_changed(*args):
            value = params.ramp_on_slow.value and params.enable_slow_out.value
            self.ids.explainSweepOnAnalog.setVisible(value)
            self.ids.explainNoSweepOnAnalog.setVisible(not value)
        params.ramp_on_slow.change(ramp_on_slow_param_changed)
        params.enable_slow_out.change(ramp_on_slow_param_changed)

        def dual_channel_changed(value):
            self.ids.dual_channel_mixing.setVisible(value)
            self.ids.explain_second_channel.setVisible(value)
            self.app().main_window.ids.spectroscopy_channel_2_page.setEnabled(value)
            return value
        param2ui(
            params.dual_channel,
            self.ids.dual_channel,
            dual_channel_changed
        )

        param2ui(
            params.channel_mixing,
            self.ids.channel_mixing_slider,
            lambda value: value + 128
        )
        # this is required to update the descriptive labels in the beginning
        self.channel_mixing_changed()

        def enable_slow_out_changed(value):
            self.ids.slow_out_settings.setEnabled(value)
            return value
        param2ui(
            params.enable_slow_out,
            self.ids.enable_slow_out,
            enable_slow_out_changed
        )

        param2ui(
            params.slow_polarity_inverted,
            self.ids.slow_polarity
        )

    def ramp_on_slow_changed(self):
        self.parameters.ramp_on_slow.value = int(self.ids.rampOnSlow.checkState() > 0)
        self.control.write_data()

    def channel_mixing_changed(self):
        value = int(self.ids.channel_mixing_slider.value()) - 128
        self.parameters.channel_mixing.value = value
        self.control.write_data()

        self.update_channel_mixing_slider(value)

    def dual_channel_changed(self):
        self.parameters.dual_channel.value = int(self.ids.dual_channel.checkState() > 0)
        self.control.write_data()

    def update_channel_mixing_slider(self, value):
        a_value, b_value = convert_channel_mixing_value(value)

        self.ids.chain_a_factor.setText('%d' % a_value)
        self.ids.chain_b_factor.setText('%d' % b_value)

    def enable_slow_changed(self):
        self.parameters.enable_slow_out.value = int(self.ids.enable_slow_out.checkState() > 0)
        self.control.write_data()

    def change_slow_polarity(self, idx):
        self.parameters.slow_polarity_inverted.value = idx != 0
        self.control.write_data()
