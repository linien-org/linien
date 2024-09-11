# This file is part of Linien and based on redpid.
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

from linien_common.common import MHz, Vpp
from linien_gui.config import UI_PATH
from linien_gui.ui.spin_box import CustomDoubleSpinBoxNoSign
from linien_gui.utils import get_linien_app_instance, param2ui, ui2param
from PyQt5 import QtWidgets, uic


class OptimizationPanel(QtWidgets.QWidget):
    optimizationFailedWidget: QtWidgets.QWidget
    optimizationResetFailedStatePushButton: QtWidgets.QPushButton
    optimizationNotRunningWidget: QtWidgets.QWidget
    optimizationNotSelectingWidget: QtWidgets.QWidget
    optimizationModFreqMaxSpinBox: CustomDoubleSpinBoxNoSign
    optimizationModFreqMinSpinBox: CustomDoubleSpinBoxNoSign
    optimizationModfreqCheckBox: QtWidgets.QCheckBox
    optimizationModAmpMaxSpinBox: CustomDoubleSpinBoxNoSign
    optimizationModAmpMinSpinBox: CustomDoubleSpinBoxNoSign
    optimizationModAmpCheckBox: QtWidgets.QCheckBox
    checkBox: QtWidgets.QCheckBox
    optimizationChannelSelectorGroupBox: QtWidgets.QGroupBox
    optimizationChannelComboBox: QtWidgets.QComboBox
    startOptimizationPushButton: QtWidgets.QPushButton
    optimizationSelectingWidget: QtWidgets.QWidget
    abortOptimizationLineSelection: QtWidgets.QPushButton
    optimizationPreparingWidget: QtWidgets.QWidget
    abortOptimizationPreparing: QtWidgets.QPushButton
    optimizationPreparingLabel: QtWidgets.QLabel
    optimizationRunningWidget: QtWidgets.QWidget
    optimizationAbortPushButton: QtWidgets.QPushButton
    optimizationDisplayParametersLabel: QtWidgets.QLabel
    optimizationImprovementLabel: QtWidgets.QLabel
    useOptimizedParametersPushButton: QtWidgets.QPushButton

    def __init__(self, *args, **kwargs):
        super(OptimizationPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "optimization_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.startOptimizationPushButton.clicked.connect(self.start_optimization)
        self.useOptimizedParametersPushButton.clicked.connect(self.use_new_parameters)
        self.optimizationAbortPushButton.clicked.connect(self.abort)
        self.abortOptimizationLineSelection.clicked.connect(self.abort_selection)
        self.abortOptimizationPreparing.clicked.connect(self.abort_preparation)
        self.optimizationChannelComboBox.currentIndexChanged.connect(
            self.channel_changed
        )
        self.optimizationResetFailedStatePushButton.clicked.connect(
            self.reset_failed_state
        )

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        for element, parameter in {
            self.optimizationModFreqMinSpinBox: self.parameters.optimization_mod_freq_min,  # noqa: E501
            self.optimizationModFreqMaxSpinBox: self.parameters.optimization_mod_freq_max,  # noqa: E501
            self.optimizationModAmpMinSpinBox: self.parameters.optimization_mod_amp_min,
            self.optimizationModAmpMaxSpinBox: self.parameters.optimization_mod_amp_max,
        }.items():
            element.setKeyboardTracking(False)
            ui2param(element, parameter)
            param2ui(parameter, element)

        for element, parameter in {
            self.optimizationModfreqCheckBox: self.parameters.optimization_mod_freq_enabled,  # noqa: E501
            self.optimizationModAmpCheckBox: self.parameters.optimization_mod_amp_enabled,  # noqa: E501
        }.items():
            ui2param(element, parameter)
            param2ui(parameter, element)

        self.parameters.optimization_running.add_callback(
            self.on_optimization_running_changed
        )
        self.parameters.optimization_approaching.add_callback(
            self.on_optimization_running_changed
        )
        self.parameters.optimization_failed.add_callback(
            self.on_optimization_running_changed
        )
        self.parameters.optimization_selection.add_callback(
            self.on_optimization_selection_changed
        )
        self.parameters.modulation_amplitude.add_callback(
            self.on_modulation_parameters_changed
        )
        self.parameters.modulation_frequency.add_callback(
            self.on_modulation_parameters_changed
        )
        self.parameters.demodulation_phase_a.add_callback(
            self.on_modulation_parameters_changed
        )
        self.parameters.optimization_improvement.add_callback(
            self.on_improvement_changed
        )
        self.parameters.dual_channel.add_callback(self.on_dual_channel_changed)
        self.parameters.pid_only_mode.add_callback(self.on_pid_only_mode_changed)

    def on_optimization_running_changed(self, _):
        running = self.parameters.optimization_running.value
        approaching = self.parameters.optimization_approaching.value
        failed = self.parameters.optimization_failed.value

        self.optimizationNotRunningWidget.setVisible(not failed and not running)
        self.optimizationRunningWidget.setVisible(
            not failed and running and not approaching
        )
        self.optimizationPreparingWidget.setVisible(
            not failed and running and approaching
        )
        self.optimizationFailedWidget.setVisible(failed)

    def on_optimization_selection_changed(self, value) -> None:
        self.optimizationSelectingWidget.setVisible(value)
        self.optimizationNotSelectingWidget.setVisible(not value)

    def on_modulation_parameters_changed(self, _) -> None:
        dual_channel = self.parameters.dual_channel.value
        channel = self.parameters.optimization_channel.value
        optimized = self.parameters.optimization_optimized_parameters.value
        mod_phase = (
            self.parameters.demodulation_phase_a,
            self.parameters.demodulation_phase_b,
        )[0 if not dual_channel else (0, 1)[channel]].value
        self.optimizationDisplayParametersLabel.setText(
            (
                "<br />\n"
                "<b>current parameters</b>: "
                f"{self.parameters.modulation_frequency.value / MHz:.2f}&nbsp;MHz, "
                f"{self.parameters.modulation_amplitude.value / Vpp:.2f}&nbsp;Vpp, "
                f"{mod_phase:.2f}&nbsp;deg<br />\n"
                "<b>optimized parameters</b>: "
                f"{optimized[0] / MHz:.2f}&nbsp;MHz, "
                f"{optimized[1] / Vpp:.2f}&nbsp;Vpp, "
                f"{optimized[2]:.2f}&nbsp;deg\n"
                "<br />"
            )
        )

    def on_improvement_changed(self, improvement) -> None:
        self.optimizationImprovementLabel.setText(f"{improvement:%}")

    def on_dual_channel_changed(self, value: bool) -> None:
        self.optimizationChannelSelectorGroupBox.setVisible(value)

    def on_pid_only_mode_changed(self, pid_only_mode_enabled: bool) -> None:
        """Disable this panel if PID-only mode is enabled (nothing to optimize)."""
        self.setEnabled(not pid_only_mode_enabled)

    def start_optimization(self) -> None:
        self.parameters.optimization_selection.value = True

    def abort_selection(self) -> None:
        self.parameters.optimization_selection.value = False

    def abort_preparation(self) -> None:
        self.parameters.task.value.stop(False)

    def abort(self):
        self.parameters.task.value.stop(False)

    def use_new_parameters(self) -> None:
        self.parameters.task.value.stop(True)

    def channel_changed(self, channel) -> None:
        self.parameters.optimization_channel.value = channel

    def reset_failed_state(self) -> None:
        self.parameters.optimization_failed.value = False
