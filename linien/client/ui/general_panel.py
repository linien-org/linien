import numpy as np
from PyQt5 import QtGui
from linien.client.widgets import CustomWidget


class GeneralPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.rampOnSlow.stateChanged.connect(self.ramp_on_slow_changed)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        params.ramp_on_slow.change(
            lambda value: self.ids.rampOnSlow.setChecked(value)
        )

    def ramp_on_slow_changed(self):
        self.parameters.ramp_on_slow.value = int(self.ids.rampOnSlow.checkState() > 0)
        self.control.write_data()