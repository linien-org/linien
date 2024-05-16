# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
# Copyright 2022 Christian Freier <christian.freier@nomadatomics.com>
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

from linien_common.common import (
    ANALOG_OUT_V,
    OutputChannel,
    convert_channel_mixing_value,
)
from linien_gui.config import UI_PATH
from linien_gui.ui.spin_box import CustomDoubleSpinBoxNoSign
from linien_gui.utils import get_linien_app_instance, param2ui
from PyQt5 import QtWidgets, uic


class GeneralPanel(QtWidgets.QWidget):
    analogOutComboBox1: CustomDoubleSpinBoxNoSign
    analogOutComboBox2: CustomDoubleSpinBoxNoSign
    analogOutComboBox3: CustomDoubleSpinBoxNoSign
    pidOnlyModeCheckBox: QtWidgets.QCheckBox
    fast_in_1_status: QtWidgets.QLabel
    fast_in_2_status: QtWidgets.QLabel
    dualChannelCheckBox: QtWidgets.QCheckBox
    dualChannelMixingGroupBox: QtWidgets.QGroupBox
    channelMixingSlider: QtWidgets.QSlider
    output_ports_group: QtWidgets.QGroupBox
    controlChannelComboBox: QtWidgets.QComboBox
    sweepChannelComboBox: QtWidgets.QComboBox
    slowControlComboBox: QtWidgets.QComboBox
    polaritySelectorGroupBox: QtWidgets.QGroupBox
    polarityContainerAnalogOut0: QtWidgets.QWidget
    polarityComboBoxAnalogOut0: QtWidgets.QComboBox
    polarityContainerFastOut1: QtWidgets.QWidget
    polarityComboBoxFastOut1: QtWidgets.QComboBox
    polarityContainerFastOut2: QtWidgets.QWidget
    polarityComboBoxFastOut2: QtWidgets.QComboBox
    modulationChannelComboBox: QtWidgets.QComboBox

    def __init__(self, *args, **kwargs) -> None:
        super(GeneralPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "general_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.channelMixingSlider.valueChanged.connect(self.on_channel_mixing_changed)
        self.pidOnlyModeCheckBox.stateChanged.connect(self.on_pid_only_mode_changed)
        self.dualChannelCheckBox.stateChanged.connect(self.on_dual_channel_changed)
        self.modulationChannelComboBox.currentIndexChanged.connect(
            self.on_mod_channel_changed
        )
        self.controlChannelComboBox.currentIndexChanged.connect(
            self.on_control_channel_changed
        )
        self.sweepChannelComboBox.currentIndexChanged.connect(
            self.on_sweep_channel_changed
        )
        self.slowControlComboBox.currentIndexChanged.connect(
            self.on_slow_control_channel_changed
        )
        self.polarityComboBoxFastOut1.currentIndexChanged.connect(
            self.on_polarity_fast_out1_changed
        )
        self.polarityComboBoxFastOut2.currentIndexChanged.connect(
            self.on_polarity_fast_out2_changed
        )
        self.polarityComboBoxAnalogOut0.currentIndexChanged.connect(
            self.on_polarity_analog_out0_changed
        )

        for idx in range(1, 4):
            element: CustomDoubleSpinBoxNoSign = getattr(
                self, f"analogOutComboBox{idx}"
            )
            element.setKeyboardTracking(False)
            element.valueChanged.connect(
                lambda _, idx=idx: self.on_analog_out_changed(idx)
            )

    def on_connection_established(self) -> None:
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.parameters.pid_only_mode, self.pidOnlyModeCheckBox)

        def on_dual_channel_changed(value):
            self.dualChannelMixingGroupBox.setVisible(value)
            self.fast_in_1_status.setText(
                "error signal" if not value else "error signal 1"
            )
            self.fast_in_2_status.setText("monitor" if not value else "error signal 2")
            return value

        param2ui(
            self.parameters.dual_channel,
            self.dualChannelCheckBox,
            on_dual_channel_changed,
        )

        param2ui(
            self.parameters.channel_mixing,
            self.channelMixingSlider,
            lambda value: value + 128,
        )
        # this is required to update the descriptive labels in the beginning
        self.on_channel_mixing_changed()

        param2ui(self.parameters.mod_channel, self.modulationChannelComboBox)
        param2ui(self.parameters.control_channel, self.controlChannelComboBox)
        param2ui(self.parameters.sweep_channel, self.sweepChannelComboBox)
        param2ui(self.parameters.slow_control_channel, self.slowControlComboBox)

        param2ui(self.parameters.polarity_fast_out1, self.polarityComboBoxFastOut1)
        param2ui(self.parameters.polarity_fast_out2, self.polarityComboBoxFastOut2)
        param2ui(self.parameters.polarity_analog_out0, self.polarityComboBoxAnalogOut0)

        self.parameters.control_channel.add_callback(self.show_polarity_settings)
        self.parameters.sweep_channel.add_callback(self.show_polarity_settings)
        self.parameters.mod_channel.add_callback(self.show_polarity_settings)
        self.parameters.slow_control_channel.add_callback(self.show_polarity_settings)
        self.parameters.pid_on_slow_enabled.add_callback(self.show_polarity_settings)

        for idx in range(1, 4):
            param2ui(
                getattr(self.parameters, f"analog_out_{idx}"),
                getattr(self, f"analogOutComboBox{idx}"),
                process_value=lambda v: ANALOG_OUT_V * v,
            )

        def on_pid_only_mode_changed(pid_only_mode_enabled):
            """Disables controls that are irrelevant if PID-only mode is enabled"""
            widgets_to_disable = (
                self.output_ports_group,
                self.input_ports_group,
            )
            for widget in widgets_to_disable:
                widget.setEnabled(not pid_only_mode_enabled)

        self.parameters.pid_only_mode.add_callback(on_pid_only_mode_changed)

    def on_analog_out_changed(self, idx):
        getattr(self.parameters, f"analog_out_{idx}").value = int(
            getattr(self, f"analogOutComboBox{idx}").value() / ANALOG_OUT_V
        )
        self.control.write_registers()

    def on_channel_mixing_changed(self):
        value = int(self.channelMixingSlider.value()) - 128
        self.parameters.channel_mixing.value = value
        self.control.write_registers()

        # update channel mixing slider
        a_value, b_value = convert_channel_mixing_value(value)
        self.chain_a_factor.setText(f"{a_value}")
        self.chain_b_factor.setText(f"{b_value}")

    def on_pid_only_mode_changed(self):
        self.parameters.pid_only_mode.value = int(
            self.pidOnlyModeCheckBox.checkState() > 0
        )
        self.control.write_registers()

    def on_dual_channel_changed(self):
        self.parameters.dual_channel.value = int(
            self.dualChannelCheckBox.checkState() > 0
        )
        self.control.write_registers()

    def on_mod_channel_changed(self, channel):
        self.parameters.mod_channel.value = channel
        self.control.write_registers()

    def on_control_channel_changed(self, channel):
        self.parameters.control_channel.value = channel
        self.control.write_registers()

    def on_slow_control_channel_changed(self, channel):
        if channel > 2:
            # disabled state
            self.parameters.pid_on_slow_enabled.value = False
        else:
            self.parameters.slow_control_channel.value = channel
            self.parameters.pid_on_slow_enabled.value = True
        self.control.write_registers()

    def on_sweep_channel_changed(self, channel):
        self.parameters.sweep_channel.value = channel
        self.control.write_registers()

    def on_polarity_fast_out1_changed(self, polarity):
        self.parameters.polarity_fast_out1.value = bool(polarity)
        self.control.write_registers()

    def on_polarity_fast_out2_changed(self, polarity):
        self.parameters.polarity_fast_out2.value = bool(polarity)
        self.control.write_registers()

    def on_polarity_analog_out0_changed(self, polarity):
        self.parameters.polarity_analog_out0.value = bool(polarity)
        self.control.write_registers()

    def show_polarity_settings(self, *args):
        used_channels = {
            self.parameters.control_channel.value,
            self.parameters.sweep_channel.value,
        }

        if self.parameters.pid_on_slow_enabled.value:
            used_channels.add(self.parameters.slow_control_channel.value)

        self.polaritySelectorGroupBox.setVisible(len(used_channels) > 1)
        self.polarityContainerFastOut1.setVisible(
            OutputChannel.FAST_OUT1 in used_channels
        )
        self.polarityContainerFastOut2.setVisible(
            OutputChannel.FAST_OUT2 in used_channels
        )
        self.polarityContainerAnalogOut0.setVisible(
            OutputChannel.ANALOG_OUT0 in used_channels
        )
