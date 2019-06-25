import numpy as np
from PyQt5 import QtGui
from linien.client.widgets import CustomWidget
from linien.client.utils import param2ui


class LockStatusPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.stop_lock.clicked.connect(self.stop_autolock)
        self.ids.control_signal_history_length.setKeyboardTracking(False)
        self.ids.control_signal_history_length.valueChanged.connect(self.control_signal_history_length_changed)

    def connection_established(self):
        self.control = self.app().control
        params = self.app().parameters
        self.parameters = params

        def update_status(_):
            locked = params.lock.value
            task = params.task.value
            al_failed = params.autolock_failed.value
            running = params.autolock_running.value

            if locked or (task is not None and not al_failed):
                self.show()
            else:
                self.hide()

            explain = not running

            if task:
                watching = params.autolock_watching.value
                failed = al_failed
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

        for param in (params.lock, params.autolock_approaching, params.autolock_watching,
                params.autolock_failed, params.autolock_locked):
            param.change(update_status)

        param2ui(
            params.control_signal_history_length,
            self.ids.control_signal_history_length
        )

    def stop_autolock(self):
        if self.parameters.task.value is not None:
            self.parameters.task.value.stop()
        else:
            self.control.exposed_start_ramp()

    def control_signal_history_length_changed(self):
        self.parameters.control_signal_history_length.value = \
            self.ids.control_signal_history_length.value()