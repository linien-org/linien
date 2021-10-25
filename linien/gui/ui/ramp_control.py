import superqt
from linien.gui.widgets import CustomWidget
from PyQt5 import QtGui


class RampControlWidget(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.ramp_start_stop_button.clicked.connect(self.switch_ramp_output)
        self.ids.ramp_slider.valueChanged.connect(self.update_ramp_range)
        # NOTE: The keyboardTracking property of the QDoubleSpinBoxes has been set to
        # False, to avoid signal emission when editing the field. Signals are still
        # emitted when using the arrow buttons. See also the editingFinished method.
        self.ids.ramp_center.valueChanged.connect(self.update_ramp_center)
        self.ids.ramp_amplitude.valueChanged.connect(self.update_ramp_amplitude)

    def connection_established(self):
        self.control = self.app.control
        self.parameters = self.app.parameters

        # initialize ramp controls
        self.ids.ramp_slider.init()
        amplitude = self.parameters.ramp_amplitude.value
        center = self.parameters.center.value
        self.ids.ramp_slider.setValue((center - amplitude, center + amplitude))

        self.parameters.center.on_change(self.display_ramp_status)
        self.parameters.ramp_amplitude.on_change(self.display_ramp_status)

    def display_ramp_status(self, *args):
        center = self.parameters.center.value
        amplitude = self.parameters.ramp_amplitude.value
        min_ = center - amplitude
        max_ = center + amplitude
        # block signals to avoid infinite loops when changing ramp parameters, see
        # also param2ui
        self.ids.ramp_slider.blockSignals(True)
        self.ids.ramp_amplitude.blockSignals(True)
        self.ids.ramp_center.blockSignals(True)

        self.ids.ramp_slider.setValue((min_, max_))
        self.ids.ramp_center.setValue(center)
        self.ids.ramp_amplitude.setValue(amplitude)

        self.ids.ramp_slider.blockSignals(False)
        self.ids.ramp_center.blockSignals(False)
        self.ids.ramp_amplitude.blockSignals(False)

    def switch_ramp_output(self):
        if self.ids.ramp_start_stop_button.isChecked():
            self.ids.ramp_start_stop_button.setText("Pause")
        else:
            self.ids.ramp_start_stop_button.setText("Start")

    def update_ramp_center(self, center):
        self.parameters.center.value = center
        self.control.write_data()

    def update_ramp_amplitude(self, amplitude):
        self.parameters.ramp_amplitude.value = amplitude
        self.control.write_data()

    def update_ramp_range(self, range_):
        min_, max_ = range_
        amplitude = (max_ - min_) / 2
        center = (max_ + min_) / 2
        self.parameters.ramp_amplitude.value = amplitude
        self.parameters.center.value = center
        self.control.write_data()


class RampSlider(superqt.QDoubleRangeSlider, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self):

        # set control boundaries
        self.setMinimum(-1.0)
        self.setMaximum(1.0)
        self.setSingleStep(0.001)
