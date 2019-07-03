from PyQt5 import QtGui
from linien.client.widgets import CustomWidget
from linien.client.utils import param2ui


class LockingPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui('locking_panel.ui')

    def ready(self):
        self.ids.kp.setKeyboardTracking(False)
        self.ids.kp.valueChanged.connect(self.kp_changed)
        self.ids.ki.setKeyboardTracking(False)
        self.ids.ki.valueChanged.connect(self.ki_changed)
        self.ids.kd.setKeyboardTracking(False)
        self.ids.kd.valueChanged.connect(self.kd_changed)
        self.ids.watchLockCheckbox.stateChanged.connect(self.watch_lock_changed)
        self.ids.lock_control_container.currentChanged.connect(self.lock_mode_changed)

        self.ids.manualLockButton.clicked.connect(self.start_manual_lock)
        self.ids.autoOffsetCheckbox.stateChanged.connect(self.auto_offset_changed)

        self.ids.pid_on_slow_enabled.stateChanged.connect(self.pid_on_slow_enabled_changed)
        self.ids.pid_on_slow_strength.setKeyboardTracking(False)
        self.ids.pid_on_slow_strength.valueChanged.connect(self.pid_on_slow_strength_changed)

    def connection_established(self):
        params = self.app().parameters
        self.parameters = params
        self.control = self.app().control

        param2ui(params.p, self.ids.kp)
        param2ui(params.i, self.ids.ki)
        param2ui(params.d, self.ids.kd)

        param2ui(params.watch_lock, self.ids.watchLockCheckbox)
        param2ui(params.autolock_determine_offset, self.ids.autoOffsetCheckbox)
        param2ui(
            params.automatic_mode,
            self.ids.lock_control_container,
            lambda value: 0 if value else 1
        )
        param2ui(params.pid_on_slow_enabled, self.ids.pid_on_slow_enabled)
        param2ui(params.pid_on_slow_strength, self.ids.pid_on_slow_strength)
        def slow_pid_visibility(*args):
            self.ids.slow_pid_group.setVisible(self.parameters.enable_slow_out.value)
        params.enable_slow_out.change(slow_pid_visibility)

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

        param2ui(params.target_slope_rising, self.ids.button_slope_rising)
        param2ui(
            params.target_slope_rising,
            self.ids.button_slope_falling,
            lambda value: not value
        )

    def kp_changed(self):
        self.parameters.p.value = self.ids.kp.value()
        self.control.write_data()

    def ki_changed(self):
        self.parameters.i.value = self.ids.ki.value()
        self.control.write_data()

    def kd_changed(self):
        self.parameters.d.value = self.ids.kd.value()
        self.control.write_data()

    def watch_lock_changed(self):
        self.parameters.watch_lock.value = int(self.ids.watchLockCheckbox.checkState())

    def lock_mode_changed(self, idx):
        self.parameters.automatic_mode.value = idx == 0

    def start_manual_lock(self):
        self.parameters.target_slope_rising.value = self.ids.button_slope_rising.isChecked()
        self.control.write_data()
        self.control.start_lock()

    def auto_offset_changed(self):
        self.parameters.autolock_determine_offset.value = int(self.ids.autoOffsetCheckbox.checkState())

    def pid_on_slow_strength_changed(self):
        self.parameters.pid_on_slow_strength.value = self.ids.pid_on_slow_strength.value()
        self.control.write_data()

    def pid_on_slow_enabled_changed(self):
        self.parameters.pid_on_slow_enabled.value = \
            int(self.ids.pid_on_slow_enabled.checkState()) > 0
        self.control.write_data()