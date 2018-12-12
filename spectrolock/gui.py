import math
import numpy as np
from time import time

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.garden.graph import Graph, MeshLinePlot
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg


class PIDApp(App):
    def __init__(self, parameters, control):
        self.control = control
        self.parameters = parameters

        self.last_plot_rescale = 0
        self.plot_max = 0
        self.plot_min = np.inf

        App.__init__(self)

    def build(self):
        box = BoxLayout(spacing=10)
        box.add_widget(self.create_graph())

        settings = BoxLayout(orientation='vertical', spacing=10)
        main_buttons = BoxLayout(orientation='horizontal', size_hint=(1, None))
        frequency_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        amplitude_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        range_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        phase_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        center_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        lock_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))

        box.add_widget(settings)
        settings.add_widget(main_buttons)
        settings.add_widget(frequency_layout)
        settings.add_widget(amplitude_layout)
        settings.add_widget(range_layout)
        settings.add_widget(phase_layout)
        settings.add_widget(center_layout)
        settings.add_widget(lock_layout)

        lock_scan_buttons = [
            ToggleButton(text='Scan', group='task', state='down'),
            ToggleButton(text='Lock', group='task')
        ]
        lock_scan_buttons[0].bind(on_press=lambda e: self.start_ramp())
        lock_scan_buttons[1].bind(on_press=lambda e: self.start_lock())
        for button in lock_scan_buttons:
            main_buttons.add_widget(button)

        # frequency buttons
        frequency_buttons = [
            Button(text='-'),
            Button(text='+')
        ]
        def change_frequency(positive):
            if positive:
                self.parameters.modulation_frequency.value *= 1.1
            else:
                self.parameters.modulation_frequency.value /= 1.1
            self.control.write_data()

        frequency_buttons[0].bind(on_press=lambda e: change_frequency(False))
        frequency_buttons[1].bind(on_press=lambda e: change_frequency(True))

        frequency_display = Label()
        MHz = 0x10000000 / 8
        self.parameters.modulation_frequency.change(
            lambda value: setattr(frequency_display, 'text', '%.2f MHz' % (value / MHz))
        )
        for element in [frequency_buttons[1], frequency_display, frequency_buttons[0]]:
            frequency_layout.add_widget(element)

        # amplitude buttons
        amplitude_buttons = [
            Button(text='-'),
            Button(text='+')
        ]
        def change_amplitude(positive):
            if positive:
                self.parameters.modulation_amplitude.value *= 1.1
            else:
                self.parameters.modulation_amplitude.value /= 1.1
            self.control.write_data()

        amplitude_buttons[0].bind(on_press=lambda e: change_amplitude(False))
        amplitude_buttons[1].bind(on_press=lambda e: change_amplitude(True))

        amplitude_display = Label()
        self.parameters.modulation_amplitude.change(
            lambda value: setattr(amplitude_display, 'text', '%d' % (value))
        )
        for element in [amplitude_buttons[1], amplitude_display, amplitude_buttons[0]]:
            amplitude_layout.add_widget(element)

        # scan range buttons
        scan_range_buttons = [
            Button(text='-'),
            Button(text='+')
        ]
        def change_range(positive):
            if positive:
                self.parameters.ramp_amplitude.value *= 1.5
            else:
                self.parameters.ramp_amplitude.value /= 1.5
            self.control.write_data()

        scan_range_buttons[0].bind(on_press=lambda e: change_range(False))
        scan_range_buttons[1].bind(on_press=lambda e: change_range(True))

        scan_range_display = Label()
        self.parameters.ramp_amplitude.change(
            lambda value: setattr(scan_range_display, 'text', '%d %%' % (value * 100))
        )
        for element in [scan_range_buttons[1], scan_range_display, scan_range_buttons[0]]:
            range_layout.add_widget(element)

        # phase buttons
        phase_buttons = [
            Button(text='-'),
            Button(text='+')
        ]
        def change_phase(positive):
            delta_phase = 0x100
            if not positive:
                delta_phase *= -1
            self.parameters.demodulation_phase.value += delta_phase
            self.control.write_data()

        phase_buttons[0].bind(on_press=lambda e: change_phase(False))
        phase_buttons[1].bind(on_press=lambda e: change_phase(True))

        phase_display = Label()
        self.parameters.demodulation_phase.change(
            lambda value: setattr(phase_display, 'text', hex(value))
        )
        for element in [phase_buttons[0], phase_display, phase_buttons[1]]:
            phase_layout.add_widget(element)

        # center buttons
        center_buttons = [
            Button(text='-'),
            Button(text='+')
        ]
        def change_center(positive):
            delta_center = self.parameters.ramp_amplitude.value / 10
            if not positive:
                delta_center *= -1
            self.parameters.center.value += delta_center
            print('center is', self.parameters.center.value)
            self.control.write_data()

        center_buttons[0].bind(on_press=lambda e: change_center(False))
        center_buttons[1].bind(on_press=lambda e: change_center(True))

        center_display = Label()
        self.parameters.center.change(
            lambda value: setattr(center_display, 'text', '%.2f' % (value))
        )
        for element in [center_buttons[0], center_display, center_buttons[1]]:
            center_layout.add_widget(element)

        #self.parameters.ramp_amplitude.change(lambda v: setattr(button, 'text', str(v)))
        self.parameters.to_plot.change(self.replot)

        k = TextInput(text='1', multiline=False)
        f = TextInput(text='1e-6', multiline=False)
        def set_k(value):
            print('k', value.text)
            self.parameters.k.value = float(value.text)
            self.control.write_data()
        def set_f(value):
            print('f', value.text)
            self.parameters.f.value = float(value.text)
            self.control.write_data()
        k.bind(on_text_validate=set_k)
        f.bind(on_text_validate=set_f)
        lock_layout.add_widget(k)
        lock_layout.add_widget(f)

        return box

    def create_graph(self):
        self.graph = Graph(xlabel='X', ylabel='Y', x_ticks_minor=5,
            x_ticks_major=5000, y_ticks_major=500,
            y_grid_label=True, x_grid_label=True, padding=5,
            x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-1, ymax=1,
            size_hint=(2, 1))
        self.plot = MeshLinePlot(color=[1, 0, 0, 1])
        zero_line = MeshLinePlot(color=[1,1,1,1])
        zero_line.points = [(-1, 0), (100000, 0)]
        self.graph.add_plot(zero_line)
        self.graph.add_plot(self.plot)
        return self.graph

    def replot(self, to_plot):
        if to_plot is not None:
            self.parameters.to_plot.value = None
            self.plot.points = list(enumerate(to_plot))

            self.plot_max = np.max([-1 * self.plot_min, self.plot_max, math.ceil(np.max(to_plot))])
            self.plot_min = np.min([-1 * self.plot_max, self.plot_min, math.floor(np.min(to_plot))])

            if time() - self.last_plot_rescale > 2:
                self.graph.xmax = len(to_plot)
                self.graph.ymin = math.floor(self.plot_min)
                self.graph.ymax = math.ceil(self.plot_max)

                print('plotrange:', self.graph.ymin, self.graph.ymax)

                if self.graph.ymin == self.graph.ymax:
                    self.graph.ymax += 1

                self.last_plot_rescale = time()

    def start_ramp(self):
        self.parameters.lock.value = False
        self.control.write_data()

    def start_lock(self):
        self.parameters.lock.value = True
        self.control.write_data()
