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

        # FIXME:
        """self.ids.kp.valueChanged.connect(self.kp_changed)
        self.ids.ki.valueChanged.connect(self.ki_changed)
        self.ids.kd.valueChanged.connect(self.kd_changed)"""


        def lock_status_changed(*args):
            lock = params.lock.value
            auto = params.automatic_mode.value
            # FIXME:
            print('DISABLED!')
            return

            # hide zoom container when locked
            if lock or auto:
                self.ids.lock_status_container.show()
                self.ids.lock_control_container.hide()
            else:
                self.ids.lock_status_container.hide()
                self.ids.lock_control_container.show()

        params.lock.change(lock_status_changed)
        params.automatic_mode.change(lock_status_changed)

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

            """
            def cache_element(id_):
                if id_ not in self._cached:
                    el = getattr(self.ids, id_)
                    self._cached[id_] = el

            for id_ in ('explain_autolock', 'autolock_running', 'autolock_failed',
                        'autolock_locked', 'button_stop_autolock', 'autolock_watching',
                        'watch_lock_checkbox_container'):
                cache_element(id_)

            container = self.ids.lock_status
            container.clear_widgets()

            def show_when(element, value):
                if value:
                    container.add_widget(self._cached[element])

            show_when('watch_lock_checkbox_container', not running and not locked)
            show_when('explain_autolock', explain)
            show_when('autolock_running', running and not watching)
            show_when('autolock_failed', task and not running and failed)
            show_when('autolock_locked', not running and locked)
            show_when('autolock_watching', running and watching)
            show_when('button_stop_autolock', running or locked)"""

        params.task.change(task_changed)

    """
    FIXME:
    def set_numeric_pid_parameter(self, input, parameter):
        for i in range(2):
            try:
                parameter.value = int(input.text)
                break
            except ValueError:
                # reset the value
                input.text = str(parameter.value)

        self.control.write_data()

    def set_p(self, input):
        self.set_numeric_pid_parameter(input, self.parameters.p)

    def set_i(self, input):
        self.set_numeric_pid_parameter(input, self.parameters.i)

    def set_d(self, input):
        self.set_numeric_pid_parameter(input, self.parameters.d)
    def kp_changed(self):
        self.parameters.p = self.ids.kp.value()

    def ki_changed(self):
        self.parameters.i = self.ids.ki.value()

    def kd_changed(self):
        self.parameters.d = self.ids.kd.value()"""