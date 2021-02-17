import re
from plumbum import colors

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QListWidget, QVBoxLayout, QDialog, QMessageBox
from pyqtgraph import QtCore

from linien.client.utils import connect_ssh


class SSHCommandOutputWidget(QListWidget):
    command_ended = pyqtSignal()

    def __init__(self, *args):
        super().__init__(*args)
        self.setSelectionMode(self.NoSelection)

    def execute(self, ssh, command):
        self.stdin, self.stdout, self.stderr = ssh.exec_command(
            command, bufsize=0, get_pty=True
        )
        self.addItem(">>> %s" % command)
        self.show_output()

    def show_output(self):
        if self.stdout.channel.exit_status_ready():
            return self.command_ended.emit()
        else:
            for output in (self.stdout, self.stderr):
                toread = len(output.channel.in_buffer)
                if toread == 0:
                    continue
                buf = output.read(toread).decode("utf8").rstrip("\n")

                for part in buf.split("\n"):
                    for subpart_i, subpart in enumerate(part.split("\r")):
                        subpart = subpart.strip("\n").strip("\r").strip("\r\n")
                        if subpart:
                            print(
                                (colors.red if output == self.stderr else colors.reset)
                                | subpart
                            )
                            if subpart_i > 0:
                                # delete previous item if \r is found
                                self.takeItem(self.count() - 1)

                            self.addItem(
                                # filter out special things like color codes etc.
                                re.sub(
                                    r"\x1b(\[.*?[@-~]|\].*?(\x07|\x1b\\))", "", subpart
                                )
                            )

                self.scrollToBottom()

        QtCore.QTimer.singleShot(1000, self.show_output)


def execute_command_and_show_output(parent, host, user, password, command, callback):
    print((colors.bold | "Execute command: ") + command)

    ssh = connect_ssh(host, user, password)

    window = QDialog(parent)
    window.setWindowTitle("Installing Linien server component")
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

    widget.execute(ssh, command)

    return window


class LoadingDialog(QMessageBox):
    aborted = pyqtSignal()

    def __init__(self, parent, host):
        super().__init__(parent)

        self.setIcon(QMessageBox.Information)
        self.setText("Connecting to %s" % host)
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


def error_dialog(parent, error):
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
    do_nothing_button = box.addButton("Keep remote parameters", QMessageBox.NoRole)
    upload_button = box.addButton("Upload local parameters", QMessageBox.YesRole)

    box.exec_()

    return box.clickedButton() == upload_button