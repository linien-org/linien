from linien.gui.utils_gui import color_to_hex
import numpy as np
import pyqtgraph as pg
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal

from linien.gui.widgets import CustomWidget


class PSDTableWidget(QtGui.QTableWidget, CustomWidget):
    show_or_hide_curve = pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.uuids = []

    def connection_established(self):
        self.control = self.app().control
        self.parameters = self.app().parameters

    def add_curve(self, uuid, data, color):
        if uuid not in self.uuids:
            row_count = self.rowCount()
            self.setRowCount(row_count + 1)
            self.uuids.append(uuid)
        else:
            row_count = self.uuids.index(uuid)

        checkbox = QtGui.QCheckBox()

        checkbox.setChecked(True)
        checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")
        checkbox.stateChanged.connect(
            lambda status, uuid=uuid: self.show_or_hide_curve.emit(uuid, status > 0)
        )
        self.setCellWidget(row_count, 0, checkbox)

        display_color = QtGui.QLabel()

        display_color.setStyleSheet("background-color: " + color_to_hex(color))
        self.setCellWidget(row_count, 1, display_color)

        def create_item(text):
            item = QtGui.QTableWidgetItem(str(text))
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            return item

        time_formatted = datetime.utcfromtimestamp(data["time"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        self.setItem(row_count, 2, create_item(time_formatted))

        self.setItem(row_count, 3, create_item(data["p"]))
        self.setItem(row_count, 4, create_item(data["i"]))
        self.setItem(row_count, 5, create_item(data["d"]))
        self.setItem(row_count, 6, create_item("%.4f" % data["fitness"]))

        self.resizeColumnsToContents()

    def delete_selected_curve(self):
        current = self.currentRow()
        if not self.uuids or current == -1:
            return

        try:
            uuid = self.uuids.pop(current)
        except IndexError:
            return

        self.removeRow(current)

        # select the next row
        row_count = len(self.uuids)
        if row_count:
            if row_count > current:
                self.setCurrentCell(current, 0)
            else:
                self.setCurrentCell(current - 1, 0)

        return uuid