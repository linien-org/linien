# This file is part of Linien.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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
from linien_gui.utils import get_linien_app_instance, param2ui, ui2param
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RelockingPanel(QtWidgets.QWidget):
    automaticRelockingCheckbox: QtWidgets.QCheckBox
    watchLockCheckBox: QtWidgets.QCheckBox
    watchLockOnControlCheckBox: QtWidgets.QCheckBox
    watchLockControlMinSpinBox: CustomDoubleSpinBoxNoSign
    watchLockControlMaxSpinBox: CustomDoubleSpinBoxNoSign
    watchLockOnErrorCheckBox: QtWidgets.QCheckBox
    watchLockErrorMinSpinBox: CustomDoubleSpinBoxNoSign
    watchLockErrorMaxSpinBox: CustomDoubleSpinBoxNoSign
    watchLockMonitorCheckBox: QtWidgets.QCheckBox
    watchLockMonitorMinSpinBox: CustomDoubleSpinBoxNoSign
    watchLockMonitorMaxSpinBox: CustomDoubleSpinBoxNoSign
    plotControlThresholdCheckBox: QtWidgets.QCheckBox
    plotErrorThresholdCheckBox: QtWidgets.QCheckBox
    plotMonitorThresholdCheckBox: QtWidgets.QCheckBox

    control_thresholds_signal = pyqtSignal(bool, float, float)
    error_thresholds_signal = pyqtSignal(bool, float, float)
    monitor_thresholds_signal = pyqtSignal(bool, float, float)

    def __init__(self, *args, **kwargs) -> None:
        super(RelockingPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "relocking_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

    def on_connection_established(self) -> None:
        self.parameters = self.app.parameters
        self.settings = self.app.settings
        self.control = self.app.control

        # Connect parameters and GUI controls and vice-versa:
        self.parameters.watch_lock.add_callback(self.on_watch_lock_changed)

        ui2param(
            self.watchLockCheckBox, self.parameters.watch_lock, control=self.control
        )
        param2ui(self.parameters.watch_lock, self.watchLockCheckBox)
        ui2param(
            self.automaticRelockingCheckbox,
            self.parameters.automatic_relocking,
            control=self.control,
        )
        param2ui(self.parameters.automatic_relocking, self.automaticRelockingCheckbox)

        for channel in ("control", "error", "monitor"):
            ui2param(
                getattr(self, f"plot{channel.capitalize()}ThresholdCheckBox"),
                getattr(self.settings, f"show_{channel}_threshold"),
            )
            param2ui(
                getattr(self.settings, f"show_{channel}_threshold"),
                getattr(self, f"plot{channel.capitalize()}ThresholdCheckBox"),
            )
            ui2param(
                getattr(self, f"watchLock{channel.capitalize()}MinSpinBox"),
                getattr(self.parameters, f"watch_lock_{channel}_min"),
                control=self.control,
            )
            param2ui(
                getattr(self.parameters, f"watch_lock_{channel}_min"),
                getattr(self, f"watchLock{channel.capitalize()}MinSpinBox"),
            )
            ui2param(
                getattr(self, f"watchLock{channel.capitalize()}MaxSpinBox"),
                getattr(self.parameters, f"watch_lock_{channel}_max"),
                control=self.control,
            )
            param2ui(
                getattr(self.parameters, f"watch_lock_{channel}_max"),
                getattr(self, f"watchLock{channel.capitalize()}MaxSpinBox"),
            )
            # Connect changed parameters/settings to callback callback functions
            for param in (
                getattr(self.settings, f"show_{channel}_threshold"),
                getattr(self.parameters, f"watch_lock_{channel}_min"),
                getattr(self.parameters, f"watch_lock_{channel}_max"),
            ):
                param.add_callback(getattr(self, f"on_{channel}_thresholds_changed"))

            # connect plot widget to threshold signals
            signal = getattr(self, f"{channel}_thresholds_signal")
            slot = getattr(
                self.app.main_window.graphicsView, f"show_{channel}_thresholds"
            )
            signal.connect(slot)

    def on_watch_lock_changed(self, watch_lock_enabled: bool) -> None:
        """Disable relocking checkbox if watch lock is not enabled."""
        self.automaticRelockingCheckbox.setEnabled(watch_lock_enabled)

    def on_control_thresholds_changed(self, _) -> None:
        self.control_thresholds_signal.emit(
            self.settings.show_control_threshold.value,
            self.parameters.watch_lock_control_min.value,
            self.parameters.watch_lock_control_max.value,
        )

    def on_error_thresholds_changed(self, _) -> None:
        self.error_thresholds_signal.emit(
            self.settings.show_error_threshold.value,
            self.parameters.watch_lock_error_min.value,
            self.parameters.watch_lock_error_max.value,
        )

    def on_monitor_thresholds_changed(self, _) -> None:
        self.monitor_thresholds_signal.emit(
            self.settings.show_monitor_threshold.value,
            self.parameters.watch_lock_monitor_min.value,
            self.parameters.watch_lock_monitor_max.value,
        )
