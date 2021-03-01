import os
from PyQt5.QtWidgets import (
    QSlider,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QTabWidget,
    QRadioButton,
    QComboBox,
)
from pyqtgraph.Qt import QtGui


def param2ui(parameter, element, process_value=lambda x: x):
    """Updates ui elements according to parameter values.

    Listens to parameter changes and sets the value of `element` automatically.
    Optionally, the value can be processed using `process_value`.
    This function should be used because it automatically blocks signal
    emission from the target element; otherwise this can cause nasty
    endless loops when quickly changing a paramater multiple times.
    """

    def on_change(value, element=element):
        element.blockSignals(True)

        value = process_value(value)

        if isinstance(element, (QSlider, QSpinBox, QDoubleSpinBox)):
            element.setValue(value)
        elif isinstance(element, (QCheckBox, QRadioButton)):
            element.setChecked(value)
        elif isinstance(element, (QTabWidget, QComboBox)):
            element.setCurrentIndex(int(value))
        else:
            raise Exception("unsupported element type %s" % type(element))

        element.blockSignals(False)

    parameter.on_change(on_change)


def set_window_icon(window):
    icon_name = os.path.join(*os.path.split(__file__)[:-1], "icon.ico")
    window.setWindowIcon(QtGui.QIcon(icon_name))


def color_to_hex(color):
    result = ""
    for part_idx in range(3):
        result += ("00" + hex(color[part_idx]).lstrip("0x"))[-2:]

    return "#" + result


def hex_to_color(hex):
    hex = hex.lstrip("#")
    return tuple(int(hex[i : i + 2], 16) for i in (0, 2, 4))


class RandomColorChoser:
    def __init__(self):
        self.index = 0
        # pick one to turn into an actual colormap
        # generated using https://mokole.com/palette.html
        # and shuffled using random.shuffle
        self.lut = [
            "#2e8b57",
            "#0000ff",
            "#87cefa",
            "#ff1493",
            "#adff2f",
            "#b03060",
            "#6495ed",
            "#90ee90",
            "#dc143c",
            "#ffff00",
            "#483d8b",
            "#f08080",
            "#8b4513",
            "#00ff00",
            "#da70d6",
            "#f4a460",
            "#008000",
            "#00ff7f",
            "#808000",
            "#7b68ee",
            "#a9a9a9",
            "#ff8c00",
            "#00008b",
            "#f0e68c",
            "#ff0000",
            "#800080",
            "#2f4f4f",
            "#ff00ff",
            "#00ffff",
            "#8a2be2",
        ]

    def get(self):
        color = self.lut[self.index]
        if self.index < len(self.lut) - 1:
            self.index += 1
        else:
            self.index = 0

        return hex_to_color(color)