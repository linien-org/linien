# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

import os
from typing import TYPE_CHECKING, Any, Callable, Tuple

from linien_client.remote_parameters import RemoteParameter
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabWidget,
)
from pyqtgraph.Qt import QtGui

if TYPE_CHECKING:
    from linien_gui.app import LinienApp


def get_linien_app_instance() -> "LinienApp":
    return QtWidgets.QApplication.instance()  # type: ignore[return-value]


def param2ui(
    parameter: RemoteParameter,
    element: QtWidgets.QWidget,
    process_value: Callable[[Any], Any] = lambda x: x,
):
    """
    Updates ui elements according to parameter values.

    Listens to parameter changes and sets the value of `element` automatically.
    Optionally, the value can be processed using `process_value`. This function should
    be used because it automatically blocks signal emission from the target element;
    otherwise this can cause nasty endless loops when quickly changing a parameter
    multiple times.
    """

    def on_change(value: Any, element=element) -> None:
        element.blockSignals(True)

        value = process_value(value)

        if isinstance(element, (QSlider, QSpinBox, QDoubleSpinBox)):
            element.setValue(value)
        elif isinstance(element, (QCheckBox, QRadioButton)):
            element.setChecked(value)
        elif isinstance(element, (QTabWidget, QComboBox)):
            element.setCurrentIndex(int(value))
        else:
            raise TypeError(f"Unsupported element type {type(element)}")

        element.blockSignals(False)

    parameter.add_callback(on_change)


def set_window_icon(window: QtWidgets.QMainWindow) -> None:
    icon_name = os.path.join(*os.path.split(__file__)[:-1], "icon.ico")
    window.setWindowIcon(QtGui.QIcon(icon_name))


def color_to_hex(color: Tuple[int, int, int]) -> str:
    result = ""
    for part_idx in range(3):
        result += ("00" + hex(color[part_idx]).lstrip("0x"))[-2:]

    return "#" + result


def hex_to_color(hex_: str) -> Tuple[int, ...]:
    hex_ = hex_.lstrip("#")
    return tuple(int(hex_[i : i + 2], 16) for i in (0, 2, 4))


class RandomColorChoser:
    def __init__(self):
        self.index = 0
        # pick one to turn into an actual colormap generated using
        # ttps://mokole.com/palette.html and shuffled using random.shuffle
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
