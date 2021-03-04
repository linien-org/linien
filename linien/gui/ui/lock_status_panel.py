import numpy as np
from PyQt5 import QtGui
from linien.gui.widgets import CustomWidget
from linien.gui.utils_gui import param2ui


class LockStatusPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.stop_lock.clicked.connect(self.stop_lock)
        self.ids.control_signal_history_length.setKeyboardTracking(False)
        self.ids.control_signal_history_length.valueChanged.connect(
            self.control_signal_history_length_changed
        )

    def connection_established(self):
        self.control = self.app().control
        params = self.app().parameters
        self.parameters = params

        def update_status(_):
            locked = params.lock.value
            task = params.task.value
            al_failed = params.autolock_failed.value
            running = params.autolock_running.value
            retrying = params.autolock_retrying.value
            percentage = params.autolock_percentage.value
            preparing = params.autolock_preparing.value

            if locked or (task is not None and not al_failed):
                self.show()
            else:
                self.hide()

            if task:
                watching = params.autolock_watching.value
            else:
                running = False
                watching = False

            def set_text(text):
                self.ids.lock_status.setText(text)

            if not running and locked:
                set_text("Locked!")
            if running and watching:
                set_text("Locked! Watching continuously...")
            if running and not watching and not locked and preparing:
                if not retrying:
                    set_text(
                        "Autolock is running... Analyzing data (%d %%)" % percentage
                    )
                else:
                    set_text("Trying again to lock...")

        for param in (
            params.lock,
            params.task,
            params.autolock_running,
            params.autolock_preparing,
            params.autolock_watching,
            params.autolock_failed,
            params.autolock_locked,
            params.autolock_retrying,
            params.autolock_percentage,
        ):
            param.on_change(update_status)

        param2ui(
            params.control_signal_history_length, self.ids.control_signal_history_length
        )

    def stop_lock(self):
        self.parameters.fetch_quadratures.value = True

        if self.parameters.task.value is not None:
            # this may be autolock or psd acquisition
            self.parameters.task.value.stop()
            self.parameters.task.value = None

        self.control.exposed_start_ramp()

    def control_signal_history_length_changed(self):
        self.parameters.control_signal_history_length.value = (
            self.ids.control_signal_history_length.value()
        )
