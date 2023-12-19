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

from datetime import datetime

from linien_gui.utils import color_to_hex, get_linien_app_instance
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal


class PSDTableWidget(QtWidgets.QTableWidget):
    show_or_hide_curve = pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs):
        super(PSDTableWidget, self).__init__(*args, **kwargs)
        self.app = get_linien_app_instance()
        self.app.connection_established.connect(self.on_connection_established)

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.uuids = []

    def on_connection_established(self):
        self.parameters = self.app.parameters
        self.control = self.app.control

    def add_curve(self, uuid, data, color):
        if uuid not in self.uuids:
            row_count = self.rowCount()
            self.setRowCount(row_count + 1)
            self.uuids.append(uuid)
        else:
            row_count = self.uuids.index(uuid)

        checkbox = QtWidgets.QCheckBox()

        checkbox.setChecked(True)
        checkbox.setStyleSheet("margin-left:auto; margin-right:auto;")
        checkbox.stateChanged.connect(
            lambda status, uuid=uuid: self.show_or_hide_curve.emit(uuid, status > 0)
        )
        self.setCellWidget(row_count, 0, checkbox)

        display_color = QtWidgets.QLabel()

        display_color.setStyleSheet("background-color: " + color_to_hex(color))
        self.setCellWidget(row_count, 1, display_color)

        def create_item(text):
            item = QtWidgets.QTableWidgetItem(str(text))
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
        self.setItem(row_count, 6, create_item(f"{data['fitness']:.4f}"))

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
