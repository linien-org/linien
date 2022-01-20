import superqt
from PyQt5 import QtWidgets

from linien.gui.widgets import CustomWidget


class SweepControlWidget(QtWidgets.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        # initialize sweep slider boundaries
        self.ids.sweep_slider.init()

    def connection_established(self):
        self.control = self.app.control
        self.parameters = self.app.parameters

        self.ids.sweep_slider.valueChanged.connect(self.update_sweep_range)
        # NOTE: The keyboardTracking property of the QDoubleSpinBoxes has been set to
        # False, to avoid signal emission when editing the field. Signals are still
        # emitted when using the arrow buttons. See also the editingFinished method.
        self.ids.sweep_center.valueChanged.connect(self.update_sweep_center)
        self.ids.sweep_amplitude.valueChanged.connect(self.update_sweep_amplitude)
        self.ids.sweep_start_stop_button.clicked.connect(self.pause_or_resume_sweep)

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
        self.ids.sweep_slider.blockSignals(True)
        self.ids.sweep_amplitude.blockSignals(True)
        self.ids.sweep_center.blockSignals(True)

        self.ids.sweep_slider.setValue((min_, max_))
        self.ids.sweep_center.setValue(center)
        self.ids.sweep_amplitude.setValue(amplitude)
        if self.parameters.sweep_pause.value:
            self.ids.sweep_start_stop_button.setText("Start")
        else:
            self.ids.sweep_start_stop_button.setText("Pause")

        self.ids.sweep_slider.blockSignals(False)
        self.ids.sweep_center.blockSignals(False)
        self.ids.sweep_amplitude.blockSignals(False)

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
