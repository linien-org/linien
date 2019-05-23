import numpy as np
from PyQt5 import QtGui
from linie.client.widgets import CustomWidget


class LockStatusPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self):
        self.control = self.app().control
        params = self.app().parameters
        self.parameters = params
        self.ids.stop_lock.clicked.connect(self.stop_autolock)

        def lock_status_changed(lock):
            if lock:
                self.show()
            else:
                self.hide()

        params.lock.change(lock_status_changed)

        def task_changed(task):
            explain = not task or task.failed

            if task:
                running = task.running
                locked = task.locked
                watching = task.watching
                failed = task.failed
            else:
                running = False
                locked = False
                watching = False
                failed = False

            def set_text(text):
                self.ids.lock_status.setText(text)

            if not running and locked:
                set_text('Locked!')
            if running and watching:
                set_text('Locked! Watching continuously...')
            if task and not running and failed:
                set_text('Autolock failed!')
            if running and not watching:
                set_text('Autolock is running...')

        params.task.change(task_changed)

    def stop_autolock(self):
        self.parameters.task.value.stop()