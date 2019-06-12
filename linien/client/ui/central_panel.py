import numpy as np
from PyQt5 import QtGui
from linien.client.widgets import CustomWidget


class CentralPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self):
        self.control = self.app().control
        params = self.app().parameters
        self.parameters = params

        params.ramp_amplitude.change(
            lambda value: self.ids.scan_amplitude.setText('%d %%' % (value * 100))
        )

        def change_auto_manual_mode(auto):
            self.get_widget('manual_navigation').setVisible(not auto)
            if auto:
                self.reset_scan_amplitude()

        params.automatic_mode.change(change_auto_manual_mode)

    def increase_scan_amplitude(self):
        self.change_range(True)

    def decrease_scan_amplitude(self):
        self.change_range(False)

    def go_right(self):
        self.change_center(True)

    def go_left(self):
        self.change_center(False)

    def change_center(self, positive):
        delta_center = self.parameters.ramp_amplitude.value / 10
        if not positive:
            delta_center *= -1
        new_center = self.parameters.center.value + delta_center

        if np.abs(new_center) + self.parameters.ramp_amplitude.value > 1:
            new_center = np.sign(new_center) * (1 - self.parameters.ramp_amplitude.value)

        self.parameters.center.value = new_center
        self.control.write_data()

    def change_range(self, positive):
        if positive:
            self.parameters.ramp_amplitude.value *= 1.5
        else:
            self.parameters.ramp_amplitude.value /= 1.5
        self.control.write_data()

    def reset_scan_amplitude(self):
        self.parameters.ramp_amplitude.reset()
        self.parameters.center.reset()
        self.control.write_data()