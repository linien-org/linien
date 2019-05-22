import numpy as np
from PyQt5 import QtGui
from spectrolock.client.widgets import CustomWidget


class CentralPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self, app):
        self.app = app
        self.control = app.control
        params = app.parameters
        self.parameters = params

        self.ids.go_right.clicked.connect(lambda: self.change_center(False))
        self.ids.go_left.clicked.connect(lambda: self.change_center(True))
        self.ids.increase_scan_amplitude.clicked.connect(
            lambda: self.change_range(True)
        )
        self.ids.decrease_scan_amplitude.clicked.connect(
            lambda: self.change_range(False)
        )
        self.ids.reset_scan_amplitude.clicked.connect(self.reset_range)

        params.ramp_amplitude.change(
            lambda value: self.ids.scan_amplitude.setText('%d %%' % (value * 100))
        )

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

    def reset_range(self):
        self.parameters.ramp_amplitude.reset()
        self.parameters.center.reset()
        self.control.write_data()