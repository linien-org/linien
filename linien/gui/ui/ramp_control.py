import superqt
from linien.gui.widgets import CustomWidget


class RampSlider(superqt.QDoubleRangeSlider, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self):

        # set control boundaries
        self.setMinimum(-1.0)
        self.setMaximum(1.0)
        self.setSingleStep(0.001)
