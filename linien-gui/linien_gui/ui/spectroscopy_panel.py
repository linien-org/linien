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

from linien_common.common import HIGH_PASS_FILTER, LOW_PASS_FILTER
from linien_gui.utils import param2ui
from linien_gui.widgets import UI_PATH
from PyQt5 import QtCore, QtWidgets, uic


class SpectroscopyPanel(QtWidgets.QWidget):
    def __init__(self, *args):
        super().__init__(*args)
        uic.loadUi(UI_PATH / "spectroscopy_panel.ui", self)

        def change_filter_frequency(filter_i):
            self.get_param(f"filter_{filter_i}_frequency").value = getattr(
                self, f"filter_{filter_i}_frequency"
            ).value()
            self.control.write_registers()

        def change_filter_enabled(filter_i):
            filter_enabled = int(
                getattr(self, f"filter_{filter_i}_enabled").checkState() > 0
            )
            self.get_param(f"filter_{filter_i}_enabled").value = filter_enabled
            self.control.write_registers()

        def change_filter_type(filter_i):
            param = self.get_param(f"filter_{filter_i}_type")
            current_idx = getattr(self, f"filter_{filter_i}_type").currentIndex()
            param.value = (LOW_PASS_FILTER, HIGH_PASS_FILTER)[current_idx]
            self.control.write_registers()

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

        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        self.app = self.window().app
        self.signalOffsetSpinBox.setKeyboardTracking(False)
        self.signalOffsetSpinBox.valueChanged.connect(self.change_signal_offset)
        self.demodulationPhaseSpinBox.setKeyboardTracking(False)
        self.demodulationPhaseSpinBox.valueChanged.connect(self.change_demod_phase)
        self.demodulationFrequencyComboBox.currentIndexChanged.connect(
            self.change_demod_multiplier
        )

        for filter_i in [1, 2]:
            _get = lambda parent, attr, filter_i=filter_i: getattr(
                parent, attr.format(filter_i)
            )
            _get(self, "filter_{}_enabled").stateChanged.connect(
                _get(self, "change_filter_{}_enabled")
            )
            freq_input = _get(self, "filter_{}_frequency")
            freq_input.setKeyboardTracking(False)
            freq_input.valueChanged.connect(_get(self, "change_filter_{}_frequency"))
            _get(self, "filter_{}_type").currentIndexChanged.connect(
                _get(self, "change_filter_{}_type")
            )

        def automatic_changed(value):
            self.get_param("filter_automatic").value = value
            self.control.write_registers()

        self.automaticFilterCheckBox.stateChanged.connect(automatic_changed)

        def invert_changed(value):
            self.get_param("invert").value = bool(value)
            self.control.write_registers()

        self.invertCheckBox.stateChanged.connect(invert_changed)

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        # self.close_button.clicked.connect(self.close_app)
        # self.shutdown_button.clicked.connect(self.shutdown_server)

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
            self.automatic_filtering_enabled.setVisible(value)
            self.automatic_filtering_disabled.setVisible(not value)

        self.get_param("filter_automatic").on_change(filter_automatic_changed)

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
                lambda type_: {LOW_PASS_FILTER: 0, HIGH_PASS_FILTER: 1}[type_],
            )

    def get_param(self, name):
        return getattr(self.parameters, f"{name}_{'a' if self.channel == 0 else 'b'}")

    def change_signal_offset(self):
        self.get_param("offset").value = self.signalOffsetSpinBox.value() * 8191
        self.control.write_registers()

    def change_demod_phase(self):
        self.get_param(
            "demodulation_phase"
        ).value = self.demodulationPhaseSpinBox.value()
        self.control.write_registers()

    def change_demod_multiplier(self, idx):
        self.get_param("demodulation_multiplier").value = idx + 1
        self.control.write_registers()


class SpectroscopyChannelAPanel(SpectroscopyPanel):
    channel = 0


class SpectroscopyChannelBPanel(SpectroscopyPanel):
    channel = 1
