import os
from PyQt5.QtWidgets import QSlider, QCheckBox, QSpinBox, QDoubleSpinBox, \
    QTabWidget, QRadioButton, QComboBox
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
            raise Exception('unsupported element type %s' % type(element))

        element.blockSignals(False)

    parameter.change(on_change)


def set_window_icon(window):
    icon_name = os.path.join(*os.path.split(__file__)[:-1], 'icon.ico')
    window.setWindowIcon(QtGui.QIcon(icon_name))


def color_to_hex(color):
    result = ''
    for part_idx in range(3):
        result += ('00' + hex(color[part_idx]).lstrip('0x'))[-2:]

    return '#' + result
