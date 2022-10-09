# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
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


from typing import Callable

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QListWidget, QMessageBox, QVBoxLayout, QWidget
from pyqtgraph import QtCore


class SSHCommandOutputWidget(QListWidget):
    command_ended = pyqtSignal()

    def __init__(self, *args):
        super().__init__(*args)
        self.setSelectionMode(self.NoSelection)

    def show_stdout(self):
        # FIXME: Redirect stdout and stderr to the widget.
        # self.addItem()
        # self.scrollToBottom()
        return
        self.command_ended.emit()


def deploy_server_and_show_output(
    parent: QWidget, host: str, user: str, password: str, callback: Callable
):
    window = QDialog(parent)
    window.setWindowTitle("Deploying Linien Server")
    window.resize(800, 600)
    window_layout = QVBoxLayout(window)

    widget = SSHCommandOutputWidget(parent)
    window_layout.addWidget(widget)
    window.setLayout(window_layout)
    window.setModal(True)
    window.setWindowModality(QtCore.Qt.WindowModal)
    window.show()

    def after_command():
        window.hide()
        callback()

    widget.command_ended.connect(after_command)
    widget.show_stdout()

    return window


class LoadingDialog(QMessageBox):
    aborted = pyqtSignal()

    def __init__(self, parent: QWidget, host: str):
        super().__init__(parent)

        self.setIcon(QMessageBox.Information)
        self.setText(f"Connecting to {host}")
        self.setWindowTitle("Connecting")
        self.setModal(True)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setStandardButtons(QMessageBox.NoButton)
        self.show()

    def closeEvent(self, *args):
        self.aborted.emit()

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            self.close()


def error_dialog(parent: QWidget, error):
    return QMessageBox.question(parent, "Error", error, QMessageBox.Ok, QMessageBox.Ok)


def question_dialog(parent, question, title):
    box = QMessageBox(parent)
    box.setText(question)
    box.setWindowTitle(title)
    reply = QMessageBox.question(
        parent, title, question, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
    )

    return reply == QMessageBox.Yes


def ask_for_parameter_restore_dialog(parent, question, title):
    box = QMessageBox(parent)
    box.setText(question)
    box.setWindowTitle(title)
    # do_nothing_button
    _ = box.addButton("Keep remote parameters", QMessageBox.NoRole)
    upload_button = box.addButton("Upload local parameters", QMessageBox.YesRole)

    box.exec_()

    return box.clickedButton() == upload_button
