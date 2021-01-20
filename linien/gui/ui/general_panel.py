import numpy as np
from PyQt5 import QtGui

from linien.common import (
    ANALOG_OUT_V,
    convert_channel_mixing_value,
    FAST_OUT1,
    FAST_OUT2,
    ANALOG_OUT0,
)
from linien.gui.utils_gui import param2ui
from linien.gui.widgets import CustomWidget
from linien.client.connection import MHz, Vpp


class GeneralPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("general_panel.ui")

    def ready(self):
        self.ids.channel_mixing_slider.valueChanged.connect(self.channel_mixing_changed)
        self.ids.dual_channel.stateChanged.connect(self.dual_channel_changed)

        self.ids.mod_channel.currentIndexChanged.connect(self.mod_channel_changed)
        self.ids.control_channel.currentIndexChanged.connect(
            self.control_channel_changed
        )
        self.ids.sweep_channel.currentIndexChanged.connect(self.sweep_channel_changed)
        self.ids.slow_control_channel.currentIndexChanged.connect(
            self.slow_control_channel_changed
        )

        self.ids.polarity_fast_out1.currentIndexChanged.connect(
            self.polarity_fast_out1_changed
        )
        self.ids.polarity_fast_out2.currentIndexChanged.connect(
            self.polarity_fast_out2_changed
        )
        self.ids.polarity_analog_out0.currentIndexChanged.connect(
            self.polarity_analog_out0_changed
        )

        for idx in range(4):
            if idx == 0:
                continue
            element = getattr(self.ids, "analog_out_%d" % idx)
            element.setKeyboardTracking(False)
            element.valueChanged.connect(
                lambda value, idx=idx: self.change_analog_out(idx)
            )

    def change_analog_out(self, idx):
        name = "analog_out_%d" % idx
        getattr(self.parameters, name).value = int(
            getattr(self.ids, name).value() / ANALOG_OUT_V
        )
        self.control.write_data()

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        def dual_channel_changed(value):
            self.ids.dual_channel_mixing.setVisible(value)
            return value

        param2ui(params.dual_channel, self.ids.dual_channel, dual_channel_changed)

        param2ui(
            params.channel_mixing,
            self.ids.channel_mixing_slider,
            lambda value: value + 128,
        )
        # this is required to update the descriptive labels in the beginning
        self.channel_mixing_changed()

        param2ui(params.mod_channel, self.ids.mod_channel)
        param2ui(params.control_channel, self.ids.control_channel)
        param2ui(params.sweep_channel, self.ids.sweep_channel)
        param2ui(params.pid_on_slow_enabled, self.ids.slow_control_channel)

        param2ui(params.polarity_fast_out1, self.ids.polarity_fast_out1)
        param2ui(params.polarity_fast_out2, self.ids.polarity_fast_out2)
        param2ui(params.polarity_analog_out0, self.ids.polarity_analog_out0)

        def show_polarity_settings(*args):
            used_channels = set(
                (
                    params.control_channel.value,
                    params.sweep_channel.value,
                )
            )

            if params.pid_on_slow_enabled.value:
                used_channels.add(ANALOG_OUT0)

            self.ids.polarity_selector.setVisible(len(used_channels) > 1)

            def set_visibility(element, channel_id):
                element.setVisible(channel_id in used_channels)

            set_visibility(self.ids.polarity_container_fast_out1, FAST_OUT1)
            set_visibility(self.ids.polarity_container_fast_out2, FAST_OUT2)
            set_visibility(self.ids.polarity_container_analog_out0, ANALOG_OUT0)

        params.control_channel.on_change(show_polarity_settings)
        params.sweep_channel.on_change(show_polarity_settings)
        params.mod_channel.on_change(show_polarity_settings)
        params.pid_on_slow_enabled.on_change(show_polarity_settings)

        for idx in range(4):
            if idx == 0:
                continue
            name = "analog_out_%d" % idx
            param2ui(
                getattr(params, name),
                getattr(self.ids, name),
                process_value=lambda v: ANALOG_OUT_V * v,
            )

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

        self.ids.chain_a_factor.setText("%d" % a_value)
        self.ids.chain_b_factor.setText("%d" % b_value)

    def mod_channel_changed(self, channel):
        self.parameters.mod_channel.value = channel
        self.control.write_data()

    def control_channel_changed(self, channel):
        self.parameters.control_channel.value = channel
        self.control.write_data()

    def slow_control_channel_changed(self, channel):
        self.parameters.pid_on_slow_enabled.value = bool(channel)
        self.control.write_data()

    def sweep_channel_changed(self, channel):
        self.parameters.sweep_channel.value = channel
        self.control.write_data()

    def polarity_fast_out1_changed(self, polarity):
        self.parameters.polarity_fast_out1.value = bool(polarity)
        self.control.write_data()

    def polarity_fast_out2_changed(self, polarity):
        self.parameters.polarity_fast_out2.value = bool(polarity)
        self.control.write_data()

    def polarity_analog_out0_changed(self, polarity):
        self.parameters.polarity_analog_out0.value = bool(polarity)
        self.control.write_data()
