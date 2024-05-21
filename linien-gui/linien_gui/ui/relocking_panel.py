# Copyright 2024 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien.
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

import logging

from linien_gui.config import UI_PATH
from linien_gui.ui.spin_box import CustomDoubleSpinBoxNoSign
from linien_gui.utils import get_linien_app_instance, param2ui
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RelockingPanel(QtWidgets.QWidget):
    automaticRelockingCheckbox: QtWidgets.QCheckBox
    lossOfLockDetectionCheckBox: QtWidgets.QCheckBox
    lossOfLockDetectionOnControlChannelCheckBox: QtWidgets.QCheckBox
    lossOfLockDetectionOnControlChannelMinSpinBox: CustomDoubleSpinBoxNoSign
    lossOfLockDetectionOnControlChannelMaxSpinBox: CustomDoubleSpinBoxNoSign
    lossOfLockDetectionOnErrorChannelCheckBox: QtWidgets.QCheckBox
    lossOfLockDetectionOnErrorChannelMinSpinBox: CustomDoubleSpinBoxNoSign
    lossOfLockDetectionOnErrorChannelMaxSpinBox: CustomDoubleSpinBoxNoSign
    lossOfLockDetectionOnMonitorChannelCheckBox: QtWidgets.QCheckBox
    lossOfLockDetectionOnMonitorChannelMinSpinBox: CustomDoubleSpinBoxNoSign
    lossOfLockDetectionOnMonitorChannelMaxSpinBox: CustomDoubleSpinBoxNoSign
    plotControlSignalThresholdCheckBox: QtWidgets.QCheckBox
    plotErrorSignalThresholdCheckBox: QtWidgets.QCheckBox
    plotMonitorSignalThresholdCheckBox: QtWidgets.QCheckBox

    control_signal_thresholds = pyqtSignal(bool, float, float)
    error_signal_thresholds = pyqtSignal(bool, float, float)
    monitor_signal_thresholds = pyqtSignal(bool, float, float)

    def __init__(self, *args, **kwargs) -> None:
        super(RelockingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "relocking_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.lossOfLockDetectionCheckBox.stateChanged.connect(
            self.on_watch_lock_changed
        )
        self.automaticRelockingCheckbox.stateChanged.connect(
            self.on_automatic_relocking_changed
        )
        self.lossOfLockDetectionOnControlChannelMinSpinBox.valueChanged.connect(
            self.on_watch_lock_control_min_changed
        )
        self.lossOfLockDetectionOnControlChannelMaxSpinBox.valueChanged.connect(
            self.on_watch_lock_control_max_changed
        )
        self.lossOfLockDetectionOnErrorChannelMinSpinBox.valueChanged.connect(
            self.on_watch_lock_error_min_changed
        )
        self.lossOfLockDetectionOnErrorChannelMaxSpinBox.valueChanged.connect(
            self.on_watch_lock_error_max_changed
        )
        self.lossOfLockDetectionOnMonitorChannelMinSpinBox.valueChanged.connect(
            self.on_watch_lock_monitor_min_changed
        )
        self.lossOfLockDetectionOnMonitorChannelMaxSpinBox.valueChanged.connect(
            self.on_watch_lock_monitor_max_changed
        )
        self.plotControlSignalThresholdCheckBox.stateChanged.connect(
            self.on_show_control_signal_thresholds
        )
        self.plotErrorSignalThresholdCheckBox.stateChanged.connect(
            self.on_show_error_signal_thresholds
        )
        self.plotMonitorSignalThresholdCheckBox.stateChanged.connect(
            self.on_show_monitor_signal_thresholds
        )

    def on_connection_established(self) -> None:
        self.parameters = self.app.parameters
        self.control = self.app.control

        def on_watch_lock_changed(watch_lock_enabled: bool) -> None:
            """Disables relocking checkbox if watch lock is not enabled."""
            self.automaticRelockingCheckbox.setEnabled(watch_lock_enabled)

        self.parameters.watch_lock.add_callback(on_watch_lock_changed)

        self.parameters.pid_only_mode.add_callback(on_watch_lock_changed)
        param2ui(self.parameters.watch_lock, self.lossOfLockDetectionCheckBox)
        param2ui(self.parameters.automatic_relocking, self.automaticRelockingCheckbox)
        param2ui(
            self.parameters.watch_lock_control_min,
            self.lossOfLockDetectionOnControlChannelMinSpinBox,
            process_value=lambda x: 100 * x,
        )
        param2ui(
            self.parameters.watch_lock_control_max,
            self.lossOfLockDetectionOnControlChannelMaxSpinBox,
            process_value=lambda x: 100 * x,
        )
        param2ui(
            self.parameters.watch_lock_error_min,
            self.lossOfLockDetectionOnErrorChannelMinSpinBox,
            process_value=lambda x: 100 * x,
        )
        param2ui(
            self.parameters.watch_lock_error_max,
            self.lossOfLockDetectionOnErrorChannelMaxSpinBox,
            process_value=lambda x: 100 * x,
        )
        param2ui(
            self.parameters.watch_lock_monitor_min,
            self.lossOfLockDetectionOnControlChannelMinSpinBox,
            process_value=lambda x: 100 * x,
        )
        param2ui(
            self.parameters.watch_lock_monitor_max,
            self.lossOfLockDetectionOnMonitorChannelMaxSpinBox,
            process_value=lambda x: 100 * x,
        )

        self.control_signal_thresholds.connect(
            self.app.main_window.graphicsView.show_control_signal_thresholds
        )
        self.error_signal_thresholds.connect(
            self.app.main_window.graphicsView.show_error_signal_thresholds
        )
        self.monitor_signal_thresholds.connect(
            self.app.main_window.graphicsView.show_monitor_signal_thresholds
        )

    def on_watch_lock_changed(self):
        self.parameters.watch_lock.value = int(
            self.lossOfLockDetectionCheckBox.checkState() > 0
        )
        self.control.write_registers()

    def on_automatic_relocking_changed(self):
        self.parameters.automatic_relocking.value = int(
            self.automaticRelockingCheckbox.checkState() > 0
        )
        self.control.write_registers()

    def on_watch_lock_control_min_changed(self):
        self.parameters.watch_lock_control_min.value = (
            self.lossOfLockDetectionOnControlChannelMinSpinBox.value() / 100
        )
        self.control.write_registers()

    def on_watch_lock_control_max_changed(self):
        self.parameters.watch_lock_control_max.value = (
            self.lossOfLockDetectionOnControlChannelMaxSpinBox.value() / 100
        )
        self.control.write_registers()

    def on_watch_lock_error_min_changed(self):
        self.parameters.watch_lock_error_min.value = (
            self.lossOfLockDetectionOnErrorChannelMinSpinBox.value() / 100
        )
        self.control.write_registers()

    def on_watch_lock_error_max_changed(self):
        self.parameters.watch_lock_error_max.value = (
            self.lossOfLockDetectionOnErrorChannelMaxSpinBox.value() / 100
        )
        self.control.write_registers()

    def on_watch_lock_monitor_min_changed(self):
        self.parameters.watch_lock_control_min.value = (
            self.lossOfLockDetectionOnControlChannelMinSpinBox.value() / 100
        )
        self.control.write_registers()

    def on_watch_lock_monitor_max_changed(self):
        self.parameters.watch_lock_monitor_max.value = (
            self.lossOfLockDetectionOnMonitorChannelMaxSpinBox.value() / 100
        )
        self.control.write_registers()

    def on_show_control_signal_thresholds(self) -> None:
        min_ = self.parameters.watch_lock_control_min.value
        max_ = self.parameters.watch_lock_control_max.value
        if self.plotControlSignalThresholdCheckBox.checkState() > 0:
            self.control_signal_thresholds.emit(True, min_, max_)
        else:
            self.control_signal_thresholds.emit(False, min_, max_)

    def on_show_error_signal_thresholds(self) -> None:
        min_ = self.parameters.watch_lock_error_min.value
        max_ = self.parameters.watch_lock_error_max.value
        if self.plotErrorSignalThresholdCheckBox.checkState() > 0:
            self.control_signal_thresholds.emit(True, min_, max_)
        else:
            self.error_signal_thresholds.emit(False, min_, max_)

    def on_show_monitor_signal_thresholds(self) -> None:
        min_ = self.parameters.watch_lock_monitor_min.value
        max_ = self.parameters.watch_lock_monitor_max.value
        if self.plotMonitorSignalThresholdCheckBox.checkState() > 0:
            self.monitor_signal_thresholds.emit(True, min_, max_)
        else:
            self.monitor_signal_thresholds.emit(False, min_, max_)
