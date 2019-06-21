import paramiko

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QListWidget, QVBoxLayout, QLabel, QPushButton, QListWidgetItem, \
    QHBoxLayout, QDialog, QMessageBox
from pyqtgraph import QtCore

from linien.client.utils import connect_ssh


class SSHCommandOutputWidget(QListWidget):
    command_ended = pyqtSignal()

    def __init__(self, *args):
        super().__init__(*args)
        self.setSelectionMode(self.NoSelection)

    def execute(self, ssh, command):
        self.stdin, self.stdout, self.stderr = ssh.exec_command(command)
        self.addItem('>>> %s' % command)
        self.show_output()

    def show_output(self):
        if self.stdout.channel.exit_status_ready():
            return self.command_ended.emit()
        else:
            for output in (self.stdout, self.stderr):
                buf = b''
                while output.channel.recv_ready():
                    buf += output.read(1)

                if buf:
                    self.addItem(buf.decode('utf8').rstrip('\n'))
                    self.scrollToBottom()

        QtCore.QTimer.singleShot(100, lambda: self.show_output())


def execute_command(parent, host, user, password, command, callback):
    ssh = connect_ssh(host, user, password)

    window = QDialog(parent)
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
        self.setText('Connecting to %s' % host)
        self.setWindowTitle('Connecting')
        self.setModal(True)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setStandardButtons(QMessageBox.NoButton)
        self.show()

    def closeEvent(self, *args):
        self.aborted.emit()


def error_dialog(parent, error):
    return QMessageBox.question(
        parent, 'Error', error,
        QMessageBox.Ok,
        QMessageBox.Ok
    )


def question_dialog(parent, question):
    reply = QMessageBox.question(
        parent, 'Error', question,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )

    return reply == QMessageBox.Yes