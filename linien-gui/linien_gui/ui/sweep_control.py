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

import superqt
from linien_gui.widgets import CustomWidget
from PyQt5 import QtCore, QtWidgets


class SweepControlWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        # initialize sweep slider boundaries
        self.app = self.window()._app
        self.ids = self.app.main_window
        self.ids.sweepSlider.init()
        self.app.connection_established.connect(self.on_connection_established)

    def on_connection_established(self):
        self.control = self.app.control
        self.parameters = self.app.parameters

        self.ids.sweepSlider.valueChanged.connect(self.update_sweep_range)
        # NOTE: The keyboardTracking property of the QDoubleSpinBoxes has been set to
        # False, to avoid signal emission when editing the field. Signals are still
        # emitted when using the arrow buttons. See also the editingFinished method.
        self.ids.sweepCenterSpinBox.valueChanged.connect(self.update_sweep_center)
        self.ids.sweepAmplitudeSpinBox.valueChanged.connect(self.update_sweep_amplitude)
        self.ids.sweepStartStopPushButton.clicked.connect(self.pause_or_resume_sweep)

        # initialize sweep controls
        self.display_sweep_status()

        # change displayed values when sweep parameters change
        self.parameters.sweep_center.on_change(self.display_sweep_status)
        self.parameters.sweep_amplitude.on_change(self.display_sweep_status)
        self.parameters.sweep_pause.on_change(self.display_sweep_status)

    def display_sweep_status(self, *args):
        center = self.parameters.sweep_center.value
        amplitude = self.parameters.sweep_amplitude.value
        min_ = center - amplitude
        max_ = center + amplitude

        # block signals to avoid infinite loops when changing sweep parameters, see also
        # param2ui
        self.ids.sweepSlider.blockSignals(True)
        self.ids.sweepAmplitudeSpinBox.blockSignals(True)
        self.ids.sweepCenterSpinBox.blockSignals(True)

        self.ids.sweepSlider.setValue((min_, max_))
        self.ids.sweepCenterSpinBox.setValue(center)
        self.ids.sweepAmplitudeSpinBox.setValue(amplitude)
        if self.parameters.sweep_pause.value:
            self.ids.sweepStartStopPushButton.setText("Start")
        else:
            self.ids.sweepStartStopPushButton.setText("Pause")

        self.ids.sweepSlider.blockSignals(False)
        self.ids.sweepCenterSpinBox.blockSignals(False)
        self.ids.sweepAmplitudeSpinBox.blockSignals(False)

    def pause_or_resume_sweep(self):
        # If sweep is paused, resume it or vice versa.
        self.parameters.sweep_pause.value = not self.parameters.sweep_pause.value
        self.control.write_registers()

    def update_sweep_center(self, center):
        self.parameters.sweep_center.value = center
        self.control.write_registers()

    def update_sweep_amplitude(self, amplitude):
        self.parameters.sweep_amplitude.value = amplitude
        self.control.write_registers()

    def update_sweep_range(self, range_):
        min_, max_ = range_
        amplitude = (max_ - min_) / 2
        center = (max_ + min_) / 2
        self.parameters.sweep_amplitude.value = amplitude
        self.parameters.sweep_center.value = center
        self.control.write_registers()


class SweepSlider(superqt.QDoubleRangeSlider, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self):
        # set control boundaries
        self.setMinimum(-1.0)
        self.setMaximum(1.0)
        self.setSingleStep(0.001)
