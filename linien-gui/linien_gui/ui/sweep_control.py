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
from linien_gui.utils import get_linien_app_instance
from PyQt5 import QtCore, QtWidgets


class SweepControlWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(SweepControlWidget, self).__init__(*args, **kwargs)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)
        QtCore.QTimer.singleShot(100, self.ready)

    def ready(self):
        self.main_window = self.app.main_window
        self.main_window.sweepSlider.ready()  # initialize sweep slider boundaries

    def on_connection_established(self):
        self.control = self.app.control
        self.parameters = self.app.parameters

        self.main_window.sweepSlider.valueChanged.connect(self.update_sweep_range)
        # NOTE: The keyboardTracking property of the QDoubleSpinBoxes has been set to
        # False, to avoid signal emission when editing the field. Signals are still
        # emitted when using the arrow buttons. See also the editingFinished method.
        self.main_window.sweepCenterSpinBox.valueChanged.connect(
            self.update_sweep_center
        )
        self.main_window.sweepAmplitudeSpinBox.valueChanged.connect(
            self.update_sweep_amplitude
        )
        self.main_window.sweepStartStopPushButton.clicked.connect(
            self.pause_or_resume_sweep
        )

        # initialize sweep controls
        self.display_sweep_status()

        # change displayed values when sweep parameters change
        self.parameters.sweep_center.add_callback(self.display_sweep_status)
        self.parameters.sweep_amplitude.add_callback(self.display_sweep_status)
        self.parameters.sweep_pause.add_callback(self.display_sweep_status)

    def display_sweep_status(self, *args):
        center = self.parameters.sweep_center.value
        amplitude = self.parameters.sweep_amplitude.value
        min_ = center - amplitude
        max_ = center + amplitude

        # block signals to avoid infinite loops when changing sweep parameters, see also
        # param2ui
        self.main_window.sweepSlider.blockSignals(True)
        self.main_window.sweepAmplitudeSpinBox.blockSignals(True)
        self.main_window.sweepCenterSpinBox.blockSignals(True)

        self.main_window.sweepSlider.setValue((min_, max_))
        self.main_window.sweepCenterSpinBox.setValue(center)
        self.main_window.sweepAmplitudeSpinBox.setValue(amplitude)
        if self.parameters.sweep_pause.value:
            self.main_window.sweepStartStopPushButton.setText("Start")
        else:
            self.main_window.sweepStartStopPushButton.setText("Pause")

        self.main_window.sweepSlider.blockSignals(False)
        self.main_window.sweepCenterSpinBox.blockSignals(False)
        self.main_window.sweepAmplitudeSpinBox.blockSignals(False)

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


class SweepSlider(superqt.QDoubleRangeSlider):
    def __init__(self, *args, **kwargs):
        super(SweepSlider, self).__init__(*args, **kwargs)

    def ready(self):
        # set control boundaries
        self.setMinimum(-1.0)
        self.setMaximum(1.0)
        self.setSingleStep(0.001)
