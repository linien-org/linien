import os
import sys
import math
import string
import numpy as np
from time import time
from decimal import Decimal


"""class NumberInput(TextInput):
    def __init__(self, *args, **kwargs):
        super(NumberInput, self).__init__(*args, **kwargs)

    def insert_text(self, substring, from_undo=False):
        substring = ''.join([
            sub for sub in substring
            if sub in string.digits + '-'
        ])
        return super(NumberInput, self).insert_text(substring, from_undo=from_undo)


class RootElement(FloatLayout):
    def __init__(self):
        self.last_plot_rescale = 0
        self.last_plot_data = None
        self.plot_max = 0
        self.plot_min = np.inf
        self.touch_start = None

        self._cached = {}

        FloatLayout.__init__(self)

    def connected(self, parameters, control):
        self.control = control
        self.parameters = parameters

        self.display_parameter_changes()

    def display_parameter_changes(self):
        MHz = 0x10000000 / 8
        self.parameters.modulation_frequency.change(
            lambda value: setattr(self.ids.frequency_display, 'text', '%.2f MHz' % (value / MHz))
        )

        self.parameters.modulation_amplitude.change(
            lambda value: setattr(self.ids.amplitude_display, 'text', '%d' % (value))
        )

        self.parameters.ramp_speed.change(
            lambda value: setattr(self.ids.ramp_speed_display, 'text', '%d' % (value))
        )

        self.parameters.demodulation_phase.change(
            lambda value: setattr(self.ids.phase_display, 'text', hex(value))
        )

        self.parameters.ramp_amplitude.change(
            lambda value: setattr(self.ids.scan_range_display, 'text', '%d %%' % (value * 100))
        )
        self.parameters.offset.change(
            lambda value: setattr(self.ids.offset_display, 'text', '%d' % (value))
        )
        self.parameters.p.change(
            lambda value: setattr(self.ids.kp, 'text', str(value))
        )
        self.parameters.i.change(
            lambda value: setattr(self.ids.ki, 'text', str(value))
        )
        self.parameters.d.change(
            lambda value: setattr(self.ids.kd, 'text', str(value))
        )

        self.parameters.to_plot.change(self.replot)
        def lock_status_changed(*args):
            lock = self.parameters.lock.value
            auto = self.parameters.automatic_mode.value

            self.ids.scan_button.state = 'normal' if lock else 'down'
            self.ids.lock_button.state = 'normal' if not lock else 'down'

            # hide zoom container when locked
            if lock or auto:
                self.ids.zoom_container.pos_hint = {'center_x': -1000}
            else:
                self.ids.zoom_container.pos_hint = {'center_x': 0.7/2, 'y': 0.9}

            for button in [self.ids.button_go_left, self.ids.button_go_right]:
                if lock or auto:
                    button.opacity = 0
                    button.disabled = True
                else:
                    button.opacity = 1
                    button.disabled = False

        self.parameters.lock.change(lock_status_changed)
        self.parameters.automatic_mode.change(lock_status_changed)

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
            show_when('button_stop_autolock', running or locked)

        self.parameters.task.change(task_changed)

    def change_frequency(self, positive):
        if positive:
            self.parameters.modulation_frequency.value *= 1.1
        else:
            self.parameters.modulation_frequency.value /= 1.1
        self.control.write_data()

    def change_amplitude(self, positive):
        if positive:
            self.parameters.modulation_amplitude.value *= 1.1
        else:
            self.parameters.modulation_amplitude.value /= 1.1
        self.control.write_data()

    def change_phase(self, positive):
        delta_phase = 0x100
        if not positive:
            delta_phase *= -1
        self.parameters.demodulation_phase.value += delta_phase
        self.control.write_data()

    def change_ramp_speed(self, positive):
        if positive:
            self.parameters.ramp_speed.value = int(self.parameters.ramp_speed.value * 1.1)
        else:
            self.parameters.ramp_speed.value = int(self.parameters.ramp_speed.value / 1.1)

    def change_offset(self, input):
        try:
            value = int(input.text)
        except ValueError:
            input.text = str(self.parameters.offset.value)
            return

        self.parameters.offset.value = value
        self.control.write_data()

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

    def change_tab(self, automatic_mode):
        self.parameters.automatic_mode.value = automatic_mode

    def stop_autolock(self):
        self.parameters.task.value.stop()

    def shutdown(self):
        self.control.shutdown()
    sys.exit()"""


"""class PIDApp():
    def __init__(self):
        App.__init__(self)"""
class PIDApp():

    def build(self):
        self.layout = BoxLayout()
        self.add_loading()

        return self.layout

    def add_loading(self):
        self.main_element = None
        self.layout.clear_widgets()
        # FIXME: missing
        self.layout.add_widget(
            Label(text='Connecting to RedPitaya')
        )

    def connected(self, parameters, control):
        self.control = control
        self.parameters = parameters

        def do(*args):
            self.layout.clear_widgets()
            self.main_element = RootElement()
            self.layout.add_widget(self.main_element)
            self.main_element.connected(parameters, control)

        # this executes in GUI thread
        Clock.schedule_once(do, 0)


from PyQt5 import QtWidgets
from pyqtgraph.Qt import QtCore, QtGui
# add ui folder to path
sys.path += [
    os.path.join(*list(
        os.path.split(os.path.abspath(__file__))[:-1]) + ['ui']
    )
]
from spectrolock.client.widgets import CustomWidget
from spectrolock.client.ui.main_window import Ui_MainWindow

class QTApp(QtCore.QObject):
    ready = QtCore.pyqtSignal(bool)

    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        MainWindow = QtWidgets.QMainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(MainWindow)
        MainWindow.show()

        self.window = MainWindow

        self.app.aboutToQuit.connect(self.shutdown)

        super().__init__()

    def connected(self, parameters, control):
        self.control = control
        self.parameters = parameters

        self.ready.connect(self.init)
        self.ready.emit(True)

    def init(self):
        for instance in CustomWidget.instances:
            instance.connection_established(self)

        self.parameters.call_listeners()

    def get_widget(self, name):
        """Queries a widget by name."""
        return self.window.findChild(QtCore.QObject, name)

    def close(self):
        self.app.quit()

    def shutdown(self):
        self.close()
