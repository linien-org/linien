import numpy as np
from PyQt5 import QtGui
from linie.client.widgets import CustomWidget


class LockStatusPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.stop_lock.clicked.connect(self.stop_autolock)
        self.ids.control_signal_history_length.editingFinished(self.control_signal_history_length_changed)

    def connection_established(self):
        self.control = self.app().control
        params = self.app().parameters
        self.parameters = params

        def update_status(_):
            locked = params.lock.value
            task = params.task.value

            if locked or (task is not None and not task.failed):
                self.show()
            else:
                self.hide()

            explain = not task or task.failed

            if task:
                running = task.running
                watching = task.watching
                failed = task.failed
            else:
                running = False
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

        params.lock.change(update_status)
        params.task.change(update_status)

        params.control_signal_history_length.change(
            lambda value: self.ids.control_signal_history_length.setValue(value)
        )

    def stop_autolock(self):
        if self.parameters.task.value is not None:
            self.parameters.task.value.stop()
        else:
            self.control.exposed_start_ramp()

    def control_signal_history_length_changed(self, value):
        self.parameters.control_signal_history_length.value = value