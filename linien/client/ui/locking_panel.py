from PyQt5 import QtGui
from linien.client.widgets import CustomWidget


class LockingPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.kp.editingFinished.connect(self.kp_changed)
        self.ids.ki.editingFinished.connect(self.ki_changed)
        self.ids.kd.editingFinished.connect(self.kd_changed)
        self.ids.watchLockCheckbox.stateChanged.connect(self.watch_lock_changed)
        self.ids.lock_control_container.currentChanged.connect(self.lock_mode_changed)

        self.ids.manualLockButton.clicked.connect(self.start_manual_lock)

    def connection_established(self):
        params = self.app().parameters
        self.parameters = params
        self.control = self.app().control

        params.p.change(
            lambda value: self.ids.kp.setValue(value)
        )
        params.i.change(
            lambda value: self.ids.ki.setValue(value)
        )
        params.d.change(
            lambda value: self.ids.kd.setValue(value)
        )
        params.watch_lock.change(
            lambda value: self.ids.watchLockCheckbox.setChecked(value)
        )
        params.automatic_mode.change(
            lambda value: self.ids.lock_control_container.setCurrentIndex(0 if value else 1)
        )

        def lock_status_changed(_):
            locked = params.lock.value
            task = params.task.value
            al_failed = params.autolock_failed.value
            task_running = (task is not None) and (not al_failed)

            if locked or task_running:
                self.ids.lock_control_container.hide()
            else:
                self.ids.lock_control_container.show()

        for param in (params.lock, params.autolock_approaching, params.autolock_watching,
                      params.autolock_failed, params.autolock_locked):
            param.change(lock_status_changed)

        def target_slope_changed(rising):
            self.ids.button_slope_rising.setChecked(rising)
            self.ids.button_slope_falling.setChecked(not rising)
        params.target_slope_rising.change(target_slope_changed)

    def kp_changed(self):
        self.parameters.p.value = self.ids.kp.value()

    def ki_changed(self):
        self.parameters.i.value = self.ids.ki.value()

    def kd_changed(self):
        self.parameters.d.value = self.ids.kd.value()

    def watch_lock_changed(self):
        self.parameters.watch_lock.value = int(self.ids.watchLockCheckbox.checkState())

    def lock_mode_changed(self, idx):
        self.parameters.automatic_mode.value = idx == 0

    def start_manual_lock(self):
        self.parameters.target_slope_rising.value = self.ids.button_slope_rising.isChecked()
        self.control.write_data()
        self.control.start_lock()