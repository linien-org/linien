# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5 import QtWidgets

from linien.common import (
    ANALOG_OUT0,
    ANALOG_OUT_V,
    FAST_OUT1,
    FAST_OUT2,
    convert_channel_mixing_value,
)
from linien.gui.utils_gui import param2ui
from linien.gui.widgets import CustomWidget


class GeneralPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("general_panel.ui")

    def ready(self):
        self.ids.channel_mixing_slider.valueChanged.connect(self.channel_mixing_changed)
        self.ids.fast_mode.stateChanged.connect(self.fast_mode_changed)
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
        self.control.write_registers()

    def connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.parameters.fast_mode, self.ids.fast_mode)

        param2ui(self.parameters.fast_mode, self.ids.fast_mode)

        def dual_channel_changed(value):
            self.ids.dual_channel_mixing.setVisible(value)
            self.ids.fast_in_1_status.setText(
                "error signal" if not value else "error signal 1"
            )
            self.ids.fast_in_2_status.setText(
                "monitor" if not value else "error signal 2"
            )
            return value

        param2ui(
            self.parameters.dual_channel, self.ids.dual_channel, dual_channel_changed
        )

        param2ui(
            self.parameters.channel_mixing,
            self.ids.channel_mixing_slider,
            lambda value: value + 128,
        )
        # this is required to update the descriptive labels in the beginning
        self.channel_mixing_changed()

        param2ui(self.parameters.mod_channel, self.ids.mod_channel)
        param2ui(self.parameters.control_channel, self.ids.control_channel)
        param2ui(self.parameters.sweep_channel, self.ids.sweep_channel)
        param2ui(self.parameters.pid_on_slow_enabled, self.ids.slow_control_channel)

        param2ui(self.parameters.polarity_fast_out1, self.ids.polarity_fast_out1)
        param2ui(self.parameters.polarity_fast_out2, self.ids.polarity_fast_out2)
        param2ui(self.parameters.polarity_analog_out0, self.ids.polarity_analog_out0)

        def show_polarity_settings(*args):
            used_channels = set(
                (
                    self.parameters.control_channel.value,
                    self.parameters.sweep_channel.value,
                )
            )

            if self.parameters.pid_on_slow_enabled.value:
                used_channels.add(ANALOG_OUT0)

            self.ids.polarity_selector.setVisible(len(used_channels) > 1)

            def set_visibility(element, channel_id):
                element.setVisible(channel_id in used_channels)

            set_visibility(self.ids.polarity_container_fast_out1, FAST_OUT1)
            set_visibility(self.ids.polarity_container_fast_out2, FAST_OUT2)
            set_visibility(self.ids.polarity_container_analog_out0, ANALOG_OUT0)

        self.parameters.control_channel.on_change(show_polarity_settings)
        self.parameters.sweep_channel.on_change(show_polarity_settings)
        self.parameters.mod_channel.on_change(show_polarity_settings)
        self.parameters.pid_on_slow_enabled.on_change(show_polarity_settings)

        for idx in range(4):
            if idx == 0:
                continue
            name = "analog_out_%d" % idx
            param2ui(
                getattr(self.parameters, name),
                getattr(self.ids, name),
                process_value=lambda v: ANALOG_OUT_V * v,
            )

        def fast_mode_changed(fast_mode_enabled):
            """Disables controls that are irrelevant if fast mode is enabled"""
            widgets_to_disable = (
                self.ids.output_ports_group,
                self.ids.input_ports_group,
            )
            for widget in widgets_to_disable:
                widget.setEnabled(not fast_mode_enabled)

        self.parameters.fast_mode.on_change(fast_mode_changed)

    def channel_mixing_changed(self):
        value = int(self.ids.channel_mixing_slider.value()) - 128
        self.parameters.channel_mixing.value = value
        self.control.write_registers()

        self.update_channel_mixing_slider(value)

    def fast_mode_changed(self):
        self.parameters.fast_mode.value = int(self.ids.fast_mode.checkState() > 0)
        self.control.write_registers()

    def dual_channel_changed(self):
        self.parameters.dual_channel.value = int(self.ids.dual_channel.checkState() > 0)
        self.control.write_registers()

    def update_channel_mixing_slider(self, value):
        a_value, b_value = convert_channel_mixing_value(value)

        self.ids.chain_a_factor.setText("%d" % a_value)
        self.ids.chain_b_factor.setText("%d" % b_value)

    def mod_channel_changed(self, channel):
        self.parameters.mod_channel.value = channel
        self.control.write_registers()

    def control_channel_changed(self, channel):
        self.parameters.control_channel.value = channel
        self.control.write_registers()

    def slow_control_channel_changed(self, channel):
        self.parameters.pid_on_slow_enabled.value = bool(channel)
        self.control.write_registers()

    def sweep_channel_changed(self, channel):
        self.parameters.sweep_channel.value = channel
        self.control.write_registers()

    def polarity_fast_out1_changed(self, polarity):
        self.parameters.polarity_fast_out1.value = bool(polarity)
        self.control.write_registers()

    def polarity_fast_out2_changed(self, polarity):
        self.parameters.polarity_fast_out2.value = bool(polarity)
        self.control.write_registers()

    def polarity_analog_out0_changed(self, polarity):
        self.parameters.polarity_analog_out0.value = bool(polarity)
        self.control.write_registers()
