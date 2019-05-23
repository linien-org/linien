from PyQt5 import QtGui
from linie.client.widgets import CustomWidget


class LockingPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        self.ids.kp.editingFinished.connect(self.kp_changed)
        self.ids.ki.editingFinished.connect(self.ki_changed)
        self.ids.kd.editingFinished.connect(self.kd_changed)
        self.ids.watchLockCheckbox.stateChanged.connect(self.watch_lock_changed)

    def connection_established(self):
        params = self.app().parameters
        self.parameters = params

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

        def lock_status_changed(lock):
            if lock:
                self.ids.lock_control_container.hide()
            else:
                self.ids.lock_control_container.show()

        params.lock.change(lock_status_changed)

    def kp_changed(self):
        self.parameters.p.value = self.ids.kp.value()

    def ki_changed(self):
        self.parameters.i.value = self.ids.ki.value()

    def kd_changed(self):
        self.parameters.d.value = self.ids.kd.value()

    def watch_lock_changed(self):
        self.parameters.watch_lock.value = self.ids.watchLockCheckbox.checkState()