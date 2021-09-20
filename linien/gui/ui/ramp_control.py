from linien.gui.widgets import CustomWidget
import superqt


class RampSlider(superqt.QDoubleRangeSlider, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initValues(self):
        self.setMinimum(-1.0)
        self.setMaximum(1.0)
        self.setSingleStep(0.001)

        self.setValue((-1.0, 1.0))
