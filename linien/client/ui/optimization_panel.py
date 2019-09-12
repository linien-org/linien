from PyQt5 import QtGui
from linien.client.widgets import CustomWidget
from linien.client.utils import param2ui
from linien.client.connection import MHz, Vpp


class OptimizationPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.start_optimization_btn.clicked.connect(self.start_optimization)
        self.ids.optimization_use_new_parameters.clicked.connect(self.use_new_parameters)
        self.ids.optimization_abort.clicked.connect(self.abort)
        self.ids.abortOptimizationLineSelection.clicked.connect(self.abort_selection)

        for param_name in (
            'optimization_mod_freq_min', 'optimization_mod_freq_max',
            'optimization_mod_amp_min', 'optimization_mod_amp_max',
            'optimization_min_line_width'
        ):
            element = getattr(self.ids, param_name)
            element.setKeyboardTracking(False)
            def write_parameter(*args, param_name=param_name, element=element):
                getattr(self.parameters, param_name).value = element.value()
            element.valueChanged.connect(write_parameter)

    def connection_established(self):
        params = self.app().parameters
        self.parameters = params
        self.control = self.app().control

        def opt_running_changed(_):
            running = params.optimization_running.value
            approaching = params.optimization_approaching.value
            self.ids.optimization_not_running_container.setVisible(not running)
            self.ids.optimization_running_container.setVisible(running and not approaching)
            self.ids.optimization_preparing.setVisible(running and approaching)
        params.optimization_running.change(opt_running_changed)
        params.optimization_approaching.change(opt_running_changed)

        def opt_selection_changed(value):
            self.ids.optimization_selecting.setVisible(value)
            self.ids.optimization_not_selecting.setVisible(not value)
        params.optimization_selection.change(opt_selection_changed)

        def mod_param_changed(_):
            self.ids.optimization_display_parameters.setText(
                """<b>modulation frequency</b>: %.2f MHz<br />
                <b>modulation amplitude</b>: %.2f Vpp<br />
                <b>demodulation phase</b> %.2f deg
                """ % (
                    params.modulation_frequency.value / MHz,
                    params.modulation_amplitude.value / Vpp,
                    params.demodulation_phase_a.value
                )
            )

        for p in (params.modulation_amplitude, params.modulation_frequency, params.demodulation_phase_a):
            p.change(mod_param_changed)

        def improvement_changed(improvement):
            self.ids.optimization_improvement.setText('%d %%' % (improvement * 100))
        params.optimization_improvement.change(improvement_changed)

        param2ui(params.optimization_mod_freq_min, self.ids.optimization_mod_freq_min)
        param2ui(params.optimization_mod_freq_max, self.ids.optimization_mod_freq_max)
        param2ui(params.optimization_mod_amp_min, self.ids.optimization_mod_amp_min)
        param2ui(params.optimization_mod_amp_max, self.ids.optimization_mod_amp_max)
        param2ui(params.optimization_min_line_width, self.ids.optimization_min_line_width)

    def start_optimization(self):
        self.parameters.optimization_selection.value = True

    def abort_selection(self):
        self.parameters.optimization_selection.value = False

    def abort(self):
        self.parameters.task.value.stop(False)

    def use_new_parameters(self):
        self.parameters.task.value.stop(True)