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

from typing import Union

from linien_client.remote_parameters import RemoteParameter
from linien_common.common import FilterType
from linien_gui.config import UI_PATH
from linien_gui.ui.spin_box import CustomDoubleSpinBox, CustomDoubleSpinBoxNoSign
from linien_gui.utils import get_linien_app_instance, param2ui
from PyQt5 import QtWidgets, uic


class SpectroscopyPanel(QtWidgets.QWidget):
    CHANNEL: Union[str, None] = None

    automaticFilterCheckBox: QtWidgets.QCheckBox
    demodulationFrequencyComboBox: CustomDoubleSpinBoxNoSign
    demodulationPhaseSpinBox: CustomDoubleSpinBoxNoSign
    invertCheckBox: QtWidgets.QCheckBox
    manualFilterWidget: QtWidgets.QWidget
    signalOffsetSpinBox: CustomDoubleSpinBox

    def __init__(self, *args):
        super(SpectroscopyPanel, self).__init__(*args)
        uic.loadUi(UI_PATH / "spectroscopy_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        def change_filter_frequency(filter_i):
            self.get_param(f"filter_{filter_i}_frequency").value = getattr(
                self, f"filter_{filter_i}_frequency"
            ).value()
            self.control.exposed_write_registers()

        def change_filter_enabled(filter_i):
            filter_enabled = int(
                getattr(self, f"filter_{filter_i}_enabled").checkState() > 0
            )
            self.get_param(f"filter_{filter_i}_enabled").value = filter_enabled
            self.control.exposed_write_registers()

        def change_filter_type(filter_i):
            param = self.get_param(f"filter_{filter_i}_type")
            current_idx = getattr(self, f"filter_{filter_i}_type").currentIndex()
            param.value = (FilterType.LOW_PASS, FilterType.HIGH_PASS)[current_idx]
            self.control.exposed_write_registers()

        for filter_i in [1, 2]:
            for key, fct in {
                f"change_filter_{filter_i}_frequency": change_filter_frequency,
                f"change_filter_{filter_i}_enabled": change_filter_enabled,
                f"change_filter_{filter_i}_type": change_filter_type,
            }.items():
                setattr(
                    self,
                    key,
                    lambda *args, fct=fct, filter_i=filter_i: fct(filter_i),
                )

        self.signalOffsetSpinBox.setKeyboardTracking(False)
        self.signalOffsetSpinBox.valueChanged.connect(self.change_signal_offset)
        self.demodulationPhaseSpinBox.setKeyboardTracking(False)
        self.demodulationPhaseSpinBox.valueChanged.connect(self.change_demod_phase)
        self.demodulationFrequencyComboBox.currentIndexChanged.connect(
            self.change_demod_multiplier
        )

        for filter_i in [1, 2]:

            def get_(parent, attr, filter_i=filter_i):
                return getattr(parent, attr.format(filter_i))

            get_(self, "filter_{}_enabled").stateChanged.connect(
                get_(self, "change_filter_{}_enabled")
            )
            freq_input = get_(self, "filter_{}_frequency")
            freq_input.setKeyboardTracking(False)
            freq_input.valueChanged.connect(get_(self, "change_filter_{}_frequency"))
            get_(self, "filter_{}_type").currentIndexChanged.connect(
                get_(self, "change_filter_{}_type")
            )

        def automatic_changed(value):
            self.get_param("filter_automatic").value = value
            self.control.exposed_write_registers()

        self.automaticFilterCheckBox.stateChanged.connect(automatic_changed)

        def invert_changed(value):
            self.get_param("invert").value = bool(value)
            self.control.exposed_write_registers()

        self.invertCheckBox.stateChanged.connect(invert_changed)

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        param2ui(self.get_param("demodulation_phase"), self.demodulationPhaseSpinBox)
        param2ui(
            self.get_param("demodulation_multiplier"),
            self.demodulationFrequencyComboBox,
            lambda value: value - 1,
        )
        param2ui(
            self.get_param("offset"), self.signalOffsetSpinBox, lambda v: v / 8191.0
        )
        param2ui(self.get_param("invert"), self.invertCheckBox)
        param2ui(self.get_param("filter_automatic"), self.automaticFilterCheckBox)

        def filter_automatic_changed(value):
            self.manualFilterWidget.setVisible(value)
            self.manualFilterWidget.setVisible(not value)

        self.get_param("filter_automatic").add_callback(filter_automatic_changed)

        for filter_i in [1, 2]:
            param2ui(
                self.get_param(f"filter_{filter_i}_enabled"),
                getattr(self, f"filter_{filter_i}_enabled"),
            )
            param2ui(
                self.get_param(f"filter_{filter_i}_frequency"),
                getattr(self, f"filter_{filter_i}_frequency"),
            )
            param2ui(
                self.get_param(f"filter_{filter_i}_type"),
                getattr(self, f"filter_{filter_i}_type"),
                lambda type_: {FilterType.LOW_PASS: 0, FilterType.HIGH_PASS: 1}[type_],
            )

    def get_param(self, name: str) -> RemoteParameter:
        return getattr(self.parameters, f"{name}_{self.CHANNEL}")

    def change_signal_offset(self):
        self.get_param("offset").value = self.signalOffsetSpinBox.value() * 8191
        self.control.exposed_write_registers()

    def change_demod_phase(self):
        self.get_param("demodulation_phase").value = (
            self.demodulationPhaseSpinBox.value()
        )
        self.control.exposed_write_registers()

    def change_demod_multiplier(self, idx):
        self.get_param("demodulation_multiplier").value = idx + 1
        self.control.exposed_write_registers()


class SpectroscopyChannelAPanel(SpectroscopyPanel):
    CHANNEL = "a"


class SpectroscopyChannelBPanel(SpectroscopyPanel):
    CHANNEL = "b"
