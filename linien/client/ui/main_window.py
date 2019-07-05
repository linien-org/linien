import pickle
import numpy as np
from math import log
from PyQt5 import QtGui, QtWidgets, QtCore

from linien.client.utils import param2ui
from linien.client.config import COLORS
from linien.client.widgets import CustomWidget


ZOOM_STEP = .9


class MainWindow(QtGui.QMainWindow, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui('main_window.ui')

    def ready(self):
        def color_to_hex(color):
            result = ''
            for part_idx in range(3):
                result += ('00' + hex(color[part_idx]).lstrip('0x'))[-2:]

            return '#' + result

        set_color = lambda el, color: el.setStyleSheet('color: ' + color_to_hex(COLORS[color]))

        set_color(self.ids.legend_spectrum_1, 'spectroscopy1')
        set_color(self.ids.legend_spectrum_2, 'spectroscopy2')
        set_color(self.ids.legend_spectrum_combined, 'spectroscopy_combined')
        set_color(self.ids.legend_error_signal, 'spectroscopy_combined')
        set_color(self.ids.legend_control_signal, 'control_signal')
        set_color(self.ids.legend_control_signal_history, 'control_signal_history')
        set_color(self.ids.legend_slow_signal_history, 'slow_history')

        self.ids.zoom_slider.valueChanged.connect(self.change_zoom)
        self.ids.go_left_btn.clicked.connect(self.go_left)
        self.ids.go_right_btn.clicked.connect(self.go_right)

    def connection_established(self):
        self.control = self.app.control
        params = self.app.parameters
        self.parameters = params

        param2ui(
            params.ramp_amplitude,
            self.ids.zoom_slider,
            lambda amplitude: int(log(amplitude, ZOOM_STEP))
        )

        def change_manual_navigation_visibility(*args):
            al_running = params.autolock_running.value
            locked = params.lock.value

            self.get_widget('manual_navigation').setVisible(
                not al_running and not locked
            )
            self.get_widget('top_lock_panel').setVisible(locked)

        params.lock.change(change_manual_navigation_visibility)
        params.autolock_running.change(change_manual_navigation_visibility)

        params.to_plot.change(self.update_std)

        params.enable_slow_out.change(
            lambda v: self.ids.legend_slow_signal_history.setVisible(v)
        )

    def go_right(self):
        self.change_center(True)

    def go_left(self):
        self.change_center(False)

    def change_center(self, positive):
        delta_center = self.parameters.ramp_amplitude.value / 10
        if not positive:
            delta_center *= -1
        new_center = self.parameters.center.value + delta_center

        if np.abs(new_center) + self.parameters.ramp_amplitude.value > 1:
            new_center = np.sign(new_center) * (1 - self.parameters.ramp_amplitude.value)

        self.parameters.center.value = new_center
        self.control.write_data()

    def change_zoom(self, zoom):
        self.parameters.ramp_amplitude.value = ZOOM_STEP ** zoom
        self.control.write_data()

    def update_std(self, to_plot):
        if self.parameters.lock.value and to_plot:
            to_plot = pickle.loads(to_plot)
            if to_plot:
                error_signal = to_plot.get('error_signal')
                control_signal = to_plot.get('control_signal')
                if error_signal and control_signal:
                    self.ids.error_std.setText('%.2f' % np.std(error_signal))
                    self.ids.control_std.setText('%.2f' % np.std(control_signal))