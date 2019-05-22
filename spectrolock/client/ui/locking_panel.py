from PyQt5 import QtGui
from spectrolock.client.widgets import CustomWidget


class LockingPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connection_established(self, app):
        self.app = app
        params = app.parameters
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

        self.ids.kp.valueChanged.connect(self.kp_changed)
        self.ids.ki.valueChanged.connect(self.ki_changed)
        self.ids.kd.valueChanged.connect(self.kd_changed)


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