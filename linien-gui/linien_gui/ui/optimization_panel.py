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

from linien_common.common import MHz, Vpp
from linien_gui.ui.spin_box import CustomDoubleSpinBoxNoSign
from linien_gui.utils import get_linien_app_instance, param2ui
from linien_gui.widgets import UI_PATH
from PyQt5 import QtWidgets, uic


class OptimizationPanel(QtWidgets.QWidget):
    optimization_failed: QtWidgets.QWidget
    optimization_reset_failed_state: QtWidgets.QPushButton
    optimization_not_running_container: QtWidgets.QWidget
    optimization_not_selecting: QtWidgets.QWidget
    optmization_mod_freq_max: CustomDoubleSpinBoxNoSign
    optimization_mod_freq_min: CustomDoubleSpinBoxNoSign
    optmization_mod_freq: QtWidgets.QCheckBox
    optmization_mod_amp_max: CustomDoubleSpinBoxNoSign
    optimization_mod_amp_min: CustomDoubleSpinBoxNoSign
    optmization_mod_amp: QtWidgets.QCheckBox
    checkBox: QtWidgets.QCheckBox
    optimization_channel_selector_box: QtWidgets.QGroupBox
    optimizationChannelComboBox: QtWidgets.QComboBox
    startOptimizationPushButton: QtWidgets.QPushButton
    optimization_selecting: QtWidgets.QWidget
    abortOptimizationLineSelection: QtWidgets.QPushButton
    optimization_preparing: QtWidgets.QWidget
    abortOptimizationPreparing: QtWidgets.QPushButton
    optimization_preparing_text: QtWidgets.QLabel
    optimization_running_container: QtWidgets.QWidget
    optimization_abort: QtWidgets.QPushButton
    optimization_display_parameters: QtWidgets.QLabel
    optimization_improvement: QtWidgets.QLabel
    useOptimizedParametersPushButton: QtWidgets.QPushButton

    def __init__(self, *args, **kwargs):
        super(OptimizationPanel, self).__init__(*args, **kwargs)
        uic.loadUi(UI_PATH / "optimization_panel.ui", self)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.startOptimizationPushButton.clicked.connect(self.start_optimization)
        self.useOptimizedParametersPushButton.clicked.connect(self.use_new_parameters)
        self.optimization_abort.clicked.connect(self.abort)
        self.abortOptimizationLineSelection.clicked.connect(self.abort_selection)
        self.abortOptimizationPreparing.clicked.connect(self.abort_preparation)
        self.optimizationChannelComboBox.currentIndexChanged.connect(
            self.channel_changed
        )
        self.optimization_reset_failed_state.clicked.connect(self.reset_failed_state)

        for param_name in (
            "optimization_mod_freq_min",
            "optimization_mod_freq_max",
            "optimization_mod_amp_min",
            "optimization_mod_amp_max",
        ):
            element = getattr(self, param_name)
            element.setKeyboardTracking(False)

            def write_parameter(*args, param_name=param_name, element=element):
                getattr(self.parameters, param_name).value = element.value()

            element.valueChanged.connect(write_parameter)

        for param_name in ("optimization_mod_freq", "optimization_mod_amp"):

            def optim_enabled_changed(_, param_name=param_name):
                getattr(self.parameters, param_name + "_enabled").value = int(
                    getattr(self, param_name).checkState()
                )

            getattr(self, param_name).stateChanged.connect(optim_enabled_changed)

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

        def opt_running_changed(_):
            running = self.parameters.optimization_running.value
            approaching = self.parameters.optimization_approaching.value
            failed = self.parameters.optimization_failed.value

            self.optimization_not_running_container.setVisible(
                not failed and not running
            )
            self.optimization_running_container.setVisible(
                not failed and running and not approaching
            )
            self.optimization_preparing.setVisible(
                not failed and running and approaching
            )
            self.optimization_failed.setVisible(failed)

        self.parameters.optimization_running.add_callback(opt_running_changed)
        self.parameters.optimization_approaching.add_callback(opt_running_changed)
        self.parameters.optimization_failed.add_callback(opt_running_changed)

        def opt_selection_changed(value):
            self.optimization_selecting.setVisible(value)
            self.optimization_not_selecting.setVisible(not value)

        self.parameters.optimization_selection.add_callback(opt_selection_changed)

        def mod_param_changed(_):
            dual_channel = self.parameters.dual_channel.value
            channel = self.parameters.optimization_channel.value
            optimized = self.parameters.optimization_optimized_parameters.value

            self.optimization_display_parameters.setText(
                (
                    "<br />\n"
                    "<b>current parameters</b>: "
                    " %.2f&nbsp;MHz, %.2f&nbsp;Vpp, %.2f&nbsp;deg<br />\n"
                    "<b>optimized parameters</b>: "
                    "%.2f&nbsp;MHz, %.2f&nbsp;Vpp, %.2f&nbsp;deg\n"
                    "<br />"
                )
                % (
                    self.parameters.modulation_frequency.value / MHz,
                    self.parameters.modulation_amplitude.value / Vpp,
                    (
                        self.parameters.demodulation_phase_a,
                        self.parameters.demodulation_phase_b,
                    )[0 if not dual_channel else (0, 1)[channel]].value,
                    optimized[0] / MHz,
                    optimized[1] / Vpp,
                    optimized[2],
                )
            )

        for param in (
            self.parameters.modulation_amplitude,
            self.parameters.modulation_frequency,
            self.parameters.demodulation_phase_a,
        ):
            param.add_callback(mod_param_changed)

        def improvement_changed(improvement):
            self.optimization_improvement.setText(f"{improvement:%}")

        self.parameters.optimization_improvement.add_callback(improvement_changed)

        param2ui(
            self.parameters.optimization_mod_freq_enabled,
            self.optimization_mod_freq,
        )
        param2ui(
            self.parameters.optimization_mod_freq_min,
            self.optimization_mod_freq_min,
        )
        param2ui(
            self.parameters.optimization_mod_freq_max,
            self.optimization_mod_freq_max,
        )
        param2ui(
            self.parameters.optimization_mod_amp_enabled, self.optimization_mod_amp
        )
        param2ui(
            self.parameters.optimization_mod_amp_min, self.optimization_mod_amp_min
        )
        param2ui(
            self.parameters.optimization_mod_amp_max, self.optimization_mod_amp_max
        )

        def dual_channel_changed(value: bool) -> None:
            self.optimization_channel_selector_box.setVisible(value)

        self.parameters.dual_channel.add_callback(dual_channel_changed)

        def pid_only_mode_changed(pid_only_mode_enabled: bool) -> None:
            """Disable this panel if PID-only mode is enabled (nothing to optimize)."""
            self.setEnabled(not pid_only_mode_enabled)

        self.parameters.pid_only_mode.add_callback(pid_only_mode_changed)

    def start_optimization(self):
        self.parameters.optimization_selection.value = True

    def abort_selection(self):
        self.parameters.optimization_selection.value = False

    def abort_preparation(self):
        self.parameters.task.value.stop(False)

    def abort(self):
        self.parameters.task.value.stop(False)

    def use_new_parameters(self):
        self.parameters.task.value.stop(True)

    def channel_changed(self, channel):
        self.parameters.optimization_channel.value = channel

    def reset_failed_state(self):
        self.parameters.optimization_failed.value = False
