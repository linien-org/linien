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

    def connection_established(self):
        params = self.app().parameters
        self.parameters = params
        self.control = self.app().control

        def opt_running_changed(running):
            self.ids.optimization_not_running_container.setVisible(not running)
            self.ids.optimization_running_container.setVisible(running)

        params.optimization_running.change(opt_running_changed)

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
            self.ids.optimization_improvement.setText('%d %%' % improvement)
        params.optimization_improvement.change(improvement_changed)

    def start_optimization(self):
        freqs = list(sorted([
            self.ids.optimization_mod_freq_min.value() * MHz,
            self.ids.optimization_mod_freq_max.value() * MHz,
        ]))
        ampls = list(sorted([
            self.ids.optimization_mod_amp_min.value() * Vpp,
            self.ids.optimization_mod_amp_max.value() * Vpp,
        ]))
        self.control.start_optimization(
            [freqs[0], ampls[0], 0],
            [freqs[1], ampls[1], 360]
        )

    def abort(self):
        self.parameters.task.value.stop(False)

    def use_new_parameters(self):
        self.parameters.task.value.stop(True)