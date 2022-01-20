from PyQt5 import QtGui
from linien.gui.widgets import CustomWidget
from linien.gui.utils_gui import param2ui
from linien.client.connection import MHz, Vpp


class OptimizationPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("optimization_panel.ui")

    def ready(self):
        self.ids.start_optimization_btn.clicked.connect(self.start_optimization)
        self.ids.optimization_use_new_parameters.clicked.connect(
            self.use_new_parameters
        )
        self.ids.optimization_abort.clicked.connect(self.abort)
        self.ids.abortOptimizationLineSelection.clicked.connect(self.abort_selection)
        self.ids.abortOptimizationPreparing.clicked.connect(self.abort_preparation)
        self.ids.optimization_channel_selector.currentIndexChanged.connect(
            self.channel_changed
        )
        self.ids.optimization_reset_failed_state.clicked.connect(
            self.reset_failed_state
        )

        for param_name in (
            "optimization_mod_freq_min",
            "optimization_mod_freq_max",
            "optimization_mod_amp_min",
            "optimization_mod_amp_max",
        ):
            element = getattr(self.ids, param_name)
            element.setKeyboardTracking(False)

            def write_parameter(*args, param_name=param_name, element=element):
                getattr(self.parameters, param_name).value = element.value()

            element.valueChanged.connect(write_parameter)

        for param_name in ("optimization_mod_freq", "optimization_mod_amp"):

            def optim_enabled_changed(_, param_name=param_name):
                getattr(self.parameters, param_name + "_enabled").value = int(
                    getattr(self.ids, param_name).checkState()
                )

            getattr(self.ids, param_name).stateChanged.connect(optim_enabled_changed)

    def connection_established(self):
        params = self.app().parameters
        self.parameters = params
        self.control = self.app().control

        def opt_running_changed(_):
            running = params.optimization_running.value
            approaching = params.optimization_approaching.value
            failed = params.optimization_failed.value

            self.ids.optimization_not_running_container.setVisible(
                not failed and not running
            )
            self.ids.optimization_running_container.setVisible(
                not failed and running and not approaching
            )
            self.ids.optimization_preparing.setVisible(
                not failed and running and approaching
            )
            self.ids.optimization_failed.setVisible(failed)

        params.optimization_running.on_change(opt_running_changed)
        params.optimization_approaching.on_change(opt_running_changed)
        params.optimization_failed.on_change(opt_running_changed)

        def opt_selection_changed(value):
            self.ids.optimization_selecting.setVisible(value)
            self.ids.optimization_not_selecting.setVisible(not value)

        params.optimization_selection.on_change(opt_selection_changed)

        def mod_param_changed(_):
            dual_channel = params.dual_channel.value
            channel = params.optimization_channel.value
            optimized = params.optimization_optimized_parameters.value

            self.ids.optimization_display_parameters.setText(
                """<br />
                <b>current parameters</b>: %.2f&nbsp;MHz, %.2f&nbsp;Vpp, %.2f&nbsp;deg<br />
                <b>optimized parameters</b>: %.2f&nbsp;MHz, %.2f&nbsp;Vpp, %.2f&nbsp;deg
                <br />
                """
                % (
                    params.modulation_frequency.value / MHz,
                    params.modulation_amplitude.value / Vpp,
                    (params.demodulation_phase_a, params.demodulation_phase_b)[
                        0 if not dual_channel else (0, 1)[channel]
                    ].value,
                    optimized[0] / MHz,
                    optimized[1] / Vpp,
                    optimized[2],
                )
            )

        for p in (
            params.modulation_amplitude,
            params.modulation_frequency,
            params.demodulation_phase_a,
        ):
            p.on_change(mod_param_changed)

        def improvement_changed(improvement):
            self.ids.optimization_improvement.setText("%d %%" % (improvement * 100))

        params.optimization_improvement.on_change(improvement_changed)

        param2ui(params.optimization_mod_freq_enabled, self.ids.optimization_mod_freq)
        param2ui(params.optimization_mod_freq_min, self.ids.optimization_mod_freq_min)
        param2ui(params.optimization_mod_freq_max, self.ids.optimization_mod_freq_max)
        param2ui(params.optimization_mod_amp_enabled, self.ids.optimization_mod_amp)
        param2ui(params.optimization_mod_amp_min, self.ids.optimization_mod_amp_min)
        param2ui(params.optimization_mod_amp_max, self.ids.optimization_mod_amp_max)

        def dual_channel_changed(value):
            self.ids.optimization_channel_selector_box.setVisible(value)

        params.dual_channel.on_change(dual_channel_changed)

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
