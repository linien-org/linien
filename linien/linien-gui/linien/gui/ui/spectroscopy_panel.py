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

from linien.common import HIGH_PASS_FILTER, LOW_PASS_FILTER
from linien.gui.utils_gui import param2ui
from linien.gui.widgets import CustomWidget


class SpectroscopyPanel(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.load_ui("spectroscopy_panel.ui")

        def change_filter_frequency(filter_i):
            self.get_param("filter_%d_frequency" % filter_i).value = getattr(
                self.ids, "filter_%d_frequency" % filter_i
            ).value()
            self.control.write_registers()

        def change_filter_enabled(filter_i):
            filter_enabled = int(
                getattr(self.ids, "filter_%d_enabled" % filter_i).checkState() > 0
            )
            self.get_param("filter_%d_enabled" % filter_i).value = filter_enabled
            self.control.write_registers()

        def change_filter_type(filter_i):
            param = self.get_param("filter_%d_type" % filter_i)
            current_idx = getattr(self.ids, "filter_%d_type" % filter_i).currentIndex()
            param.value = (LOW_PASS_FILTER, HIGH_PASS_FILTER)[current_idx]
            self.control.write_registers()

        for filter_i in [1, 2]:
            for key, fct in {
                "change_filter_%d_frequency": change_filter_frequency,
                "change_filter_%d_enabled": change_filter_enabled,
                "change_filter_%d_type": change_filter_type,
            }.items():
                setattr(
                    self,
                    key % filter_i,
                    lambda *args, fct=fct, filter_i=filter_i: fct(filter_i),
                )

    def get_param(self, name):
        return getattr(
            self.parameters, "%s_%s" % (name, "a" if self.channel == 0 else "b")
        )

    def ready(self):
        self.ids.signal_offset.setKeyboardTracking(False)
        self.ids.signal_offset.valueChanged.connect(self.change_signal_offset)
        self.ids.demodulation_phase.setKeyboardTracking(False)
        self.ids.demodulation_phase.valueChanged.connect(self.change_demod_phase)
        self.ids.demodulation_frequency.currentIndexChanged.connect(
            self.change_demod_multiplier
        )

        for filter_i in [1, 2]:
            _get = lambda parent, attr, filter_i=filter_i: getattr(
                parent, attr % filter_i
            )
            _get(self.ids, "filter_%d_enabled").stateChanged.connect(
                _get(self, "change_filter_%d_enabled")
            )
            freq_input = _get(self.ids, "filter_%d_frequency")
            freq_input.setKeyboardTracking(False)
            freq_input.valueChanged.connect(_get(self, "change_filter_%d_frequency"))
            _get(self.ids, "filter_%d_type").currentIndexChanged.connect(
                _get(self, "change_filter_%d_type")
            )

        def automatic_changed(value):
            self.get_param("filter_automatic").value = value
            self.control.write_registers()

        self.ids.filter_automatic.stateChanged.connect(automatic_changed)

        def invert_changed(value):
            self.get_param("invert").value = bool(value)
            self.control.write_registers()

        self.ids.invert.stateChanged.connect(invert_changed)

    def connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        # self.close_button.clicked.connect(self.close_app)
        # self.shutdown_button.clicked.connect(self.shutdown_server)

        param2ui(self.get_param("demodulation_phase"), self.ids.demodulation_phase)
        param2ui(
            self.get_param("demodulation_multiplier"),
            self.ids.demodulation_frequency,
            lambda value: value - 1,
        )
        param2ui(self.get_param("offset"), self.ids.signal_offset, lambda v: v / 8191.0)
        param2ui(self.get_param("invert"), self.ids.invert)
        param2ui(self.get_param("filter_automatic"), self.ids.filter_automatic)

        def filter_automatic_changed(value):
            self.ids.automatic_filtering_enabled.setVisible(value)
            self.ids.automatic_filtering_disabled.setVisible(not value)

        self.get_param("filter_automatic").on_change(filter_automatic_changed)

        for filter_i in [1, 2]:
            param2ui(
                self.get_param("filter_%d_enabled" % filter_i),
                getattr(self.ids, "filter_%d_enabled" % filter_i),
            )
            param2ui(
                self.get_param("filter_%d_frequency" % filter_i),
                getattr(self.ids, "filter_%d_frequency" % filter_i),
            )
            param2ui(
                self.get_param("filter_%d_type" % filter_i),
                getattr(self.ids, "filter_%d_type" % filter_i),
                lambda type_: {LOW_PASS_FILTER: 0, HIGH_PASS_FILTER: 1}[type_],
            )

    def change_signal_offset(self):
        self.get_param("offset").value = self.ids.signal_offset.value() * 8191
        self.control.write_registers()

    def change_demod_phase(self):
        self.get_param("demodulation_phase").value = self.ids.demodulation_phase.value()
        self.control.write_registers()

    def change_demod_multiplier(self, idx):
        self.get_param("demodulation_multiplier").value = idx + 1
        self.control.write_registers()


class SpectroscopyChannelAPanel(SpectroscopyPanel):
    channel = 0


class SpectroscopyChannelBPanel(SpectroscopyPanel):
    channel = 1
