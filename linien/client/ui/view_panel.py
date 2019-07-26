import numpy as np
from PyQt5 import QtGui

from linien.client.utils import param2ui
from linien.client.widgets import CustomWidget


class ViewPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.autoscale_y_axis.stateChanged.connect(self.autoscale_changed)
        self.ids.y_axis_minimum.valueChanged.connect(self.y_limits_changed)
        self.ids.y_axis_maximum.valueChanged.connect(self.y_limits_changed)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        param2ui(params.autoscale_y, self.ids.autoscale_y_axis)

        def y_axis_limits_changed(value):
            min_, max_ = list(sorted(value))
            self.ids.y_axis_minimum.setValue(min_)
            self.ids.y_axis_maximum.setValue(max_)
        params.y_axis_limits.change(y_axis_limits_changed)

    def autoscale_changed(self):
        self.parameters.autoscale_y.value = int(self.ids.autoscale_y_axis.checkState())

    def y_limits_changed(self):
        self.parameters.y_axis_limits.value = (
            self.ids.y_axis_minimum.value(),
            self.ids.y_axis_maximum.value()
        )