import json
import linien
import pickle
import numpy as np
from math import log
from time import time
from PyQt5 import QtGui, QtWidgets, QtCore

import linien
from linien.common import check_plot_data
from linien.gui.utils_gui import color_to_hex, param2ui
from linien.config import N_COLORS
from linien.gui.config import COLORS
from linien.gui.widgets import CustomWidget


ZOOM_STEP = 0.9
MAX_ZOOM = 50
MIN_ZOOM = 0


def ramp_amplitude_to_zoom_step(amplitude):
    return round(log(amplitude, ZOOM_STEP))


class MainWindow(QtGui.QMainWindow, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("main_window.ui")

        self.reset_std_history()

    def show(self, host, name):
        self.setWindowTitle(
            "Linien spectroscopy lock %s: %s (%s)" % (linien.__version__, name, host)
        )
        super().show()

    def closeEvent(self, *args, **kwargs):
        self.app.close_all_secondary_windows()
        super().closeEvent(*args, **kwargs)

    def ready(self):
        # handle keyboard events
        self.setFocus()

        self.ids.zoom_slider.valueChanged.connect(self.change_zoom)
        self.ids.go_left_btn.clicked.connect(self.go_left)
        self.ids.go_right_btn.clicked.connect(self.go_right)

        self.ids.export_parameters_button.clicked.connect(
            self.export_parameters_select_file
        )
        self.ids.import_parameters_button.clicked.connect(self.import_parameters)

        def display_power(power, element):
            if power != -1000:
                text = "%.2f" % power
            else:
                text = "NaN"
            element.setText(text)

        def display_power_channel_1(power):
            display_power(power, self.ids.power_channel_1)

        def display_power_channel_2(power):
            display_power(power, self.ids.power_channel_2)

        self.ids.graphicsView.signal_power1.connect(display_power_channel_1)
        self.ids.graphicsView.signal_power2.connect(display_power_channel_2)
        self.ids.graphicsView.keyPressed.connect(self.handle_key_press)

        # by default we hide it and just show when a new version is available
        self.ids.new_version_available_label.hide()

    def show_new_version_available(self):
        self.ids.new_version_available_label.show()

    def keyPressEvent(self, event):
        self.handle_key_press(event.key())

    def handle_key_press(self, key):
        print("key pressed", key)

        def click_if_enabled(btn):
            if btn.isEnabled():
                btn.clicked.emit()

        if key == ord("+"):
            self.increase_or_decrease_zoom(+1)
        elif key == ord("-"):
            self.increase_or_decrease_zoom(-1)
        elif key == QtCore.Qt.Key_Right:
            click_if_enabled(self.ids.go_right_btn)
        elif key == QtCore.Qt.Key_Left:
            click_if_enabled(self.ids.go_left_btn)

    def increase_or_decrease_zoom(self, direction):
        amplitude = self.parameters.ramp_amplitude.value
        zoom_level = ramp_amplitude_to_zoom_step(amplitude)
        zoom_level += direction
        if zoom_level < MIN_ZOOM or zoom_level > MAX_ZOOM:
            return
        self.change_zoom(zoom_level)

    def export_parameters_select_file(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".json"
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            "JSON (*%s)" % default_ext,
            options=options,
        )
        if fn:
            if not fn.endswith(default_ext):
                fn = fn + default_ext

            with open(fn, "w") as f:
                json.dump(
                    {
                        "linien-version": linien.__version__,
                        "time": time(),
                        "parameters": dict(
                            (k, getattr(self.parameters, k).value)
                            for k in self.parameters.remote.exposed_get_restorable_parameters()
                        ),
                    },
                    f,
                )

    def import_parameters(self):
        options = QtWidgets.QFileDialog.Options()
        # options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = ".json"
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            "JSON (*%s)" % default_ext,
            options=options,
        )
        if fn:
            with open(fn, "r") as f:
                data = json.load(f)

            assert "linien-version" in data, "invalid parameter file"

            restorable = self.parameters.remote.exposed_get_restorable_parameters()
            for k, v in data["parameters"].items():
                if k not in restorable:
                    print("ignore key", k)
                    continue

                print("restoring", k)
                getattr(self.parameters, k).value = v

            self.control.write_data()

    def connection_established(self):
        self.control = self.app.control
        params = self.app.parameters
        self.parameters = params

        param2ui(
            params.ramp_amplitude, self.ids.zoom_slider, ramp_amplitude_to_zoom_step
        )

        def display_ramp_range(*args):
            center = params.center.value
            amp = params.ramp_amplitude.value
            min_ = center - amp
            max_ = center + amp
            self.ids.ramp_status.setText("%.3fV to %.3fV" % (min_, max_))

        params.center.on_change(display_ramp_range)
        params.ramp_amplitude.on_change(display_ramp_range)

        def change_manual_navigation_visibility(*args):
            al_running = params.autolock_running.value
            optimization = params.optimization_running.value
            locked = params.lock.value

            self.get_widget("manual_navigation").setVisible(
                not al_running and not locked and not optimization
            )
            self.get_widget("top_lock_panel").setVisible(locked)
            self.get_widget("statusbar_unlocked").setVisible(
                not al_running and not locked and not optimization
            )

        params.lock.on_change(change_manual_navigation_visibility)
        params.autolock_running.on_change(change_manual_navigation_visibility)
        params.optimization_running.on_change(change_manual_navigation_visibility)

        params.to_plot.on_change(self.update_std)

        params.pid_on_slow_enabled.on_change(
            lambda v: self.ids.legend_slow_signal_history.setVisible(v)
        )

        self.ids.settings_toolbox.setCurrentIndex(0)

        def center_or_amplitude_changed(_):
            center = params.center.value
            amplitude = params.ramp_amplitude.value

            self.ids.go_right_btn.setEnabled(center + amplitude < 1)
            self.ids.go_left_btn.setEnabled(center - amplitude > -1)

        params.ramp_amplitude.on_change(center_or_amplitude_changed)
        params.center.on_change(center_or_amplitude_changed)

        params.lock.on_change(lambda *args: self.reset_std_history())

        def update_legend_color(*args):
            set_color = lambda el, color_name: el.setStyleSheet(
                "color: "
                + color_to_hex(
                    getattr(self.parameters, "plot_color_%d" % COLORS[color_name]).value
                )
            )

            set_color(self.ids.legend_spectrum_1, "spectrum_1")
            set_color(self.ids.legend_spectrum_2, "spectrum_2")
            set_color(self.ids.legend_spectrum_combined, "spectrum_combined")
            set_color(self.ids.legend_error_signal, "spectrum_combined")
            set_color(self.ids.legend_control_signal, "control_signal")
            set_color(self.ids.legend_control_signal_history, "control_signal_history")
            set_color(self.ids.legend_slow_signal_history, "slow_history")

        for color_idx in range(N_COLORS):
            getattr(self.parameters, "plot_color_%d" % color_idx).on_change(
                update_legend_color
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
            new_center = np.sign(new_center) * (
                1 - self.parameters.ramp_amplitude.value
            )

        print("set center", new_center)
        self.parameters.center.value = new_center
        self.control.write_data()

    def change_zoom(self, zoom):
        amplitude = ZOOM_STEP ** zoom
        print("change zoom", zoom, amplitude)
        self.parameters.ramp_amplitude.value = amplitude
        center = self.parameters.center.value
        if center + amplitude > 1:
            self.parameters.center.value = 1 - amplitude
        elif center - amplitude < -1:
            self.parameters.center.value = -1 + amplitude
        self.control.write_data()

    def update_std(self, to_plot, max_std_history_length=10):
        if self.parameters.lock.value and to_plot:
            to_plot = pickle.loads(to_plot)
            if to_plot and check_plot_data(True, to_plot):
                error_signal = to_plot.get("error_signal")
                control_signal = to_plot.get("control_signal")

                self.error_std_history.append(np.std(error_signal))
                self.control_std_history.append(np.std(control_signal))

                self.error_std_history = self.error_std_history[
                    -max_std_history_length:
                ]
                self.control_std_history = self.control_std_history[
                    -max_std_history_length:
                ]

                if error_signal is not None and control_signal is not None:
                    self.ids.error_std.setText("%.2f" % np.mean(self.error_std_history))
                    self.ids.control_std.setText(
                        "%.2f" % np.mean(self.control_std_history)
                    )

    def reset_std_history(self):
        self.error_std_history = []
        self.control_std_history = []
