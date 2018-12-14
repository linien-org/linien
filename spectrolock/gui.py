import math
import string
import numpy as np
from time import time

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.garden.graph import Graph, MeshLinePlot
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle

class NumberInput(TextInput):
    def __init__(self, *args, **kwargs):
        super(NumberInput, self).__init__(*args, **kwargs)

    def insert_text(self, substring, from_undo=False):
        substring = ''.join([
            sub for sub in substring
            if sub in string.digits + '-'
        ])
        return super(NumberInput, self).insert_text(substring, from_undo=from_undo)


class PIDApp(App):
    def __init__(self, parameters, control):
        self.control = control
        self.parameters = parameters

        self.last_plot_rescale = 0
        self.plot_max = 0
        self.plot_min = np.inf
        self.touch_start = None

        App.__init__(self)

    def build(self):
        box = FloatLayout()
        main_box = BoxLayout(orientation='horizontal', size_hint=(1, 1), spacing=10)
        center_buttons = (
            Button(text='<', size_hint=(.1, None), pos_hint={'center_y': 0.5}),
            Button(text='>', size_hint=(.1, None), pos_hint={'center_y': 0.5})
        )
        main_box.add_widget(center_buttons[0])
        main_box.add_widget(self.create_graph())
        main_box.add_widget(center_buttons[1])

        box.add_widget(main_box)

        settings = BoxLayout(orientation='vertical', spacing=10, size_hint=(0.25, 1), pos_hint={'x': 0.75, 'y': 0})
        main_buttons = BoxLayout(orientation='horizontal', size_hint=(1, None))
        frequency_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        amplitude_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        range_layout = BoxLayout(orientation='horizontal', size_hint=(None, None),
            pos_hint={'center_x': 0.7/2, 'y': 0.9}, size=((300, 25)))
        phase_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        offset_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))
        lock_layout = BoxLayout(orientation='horizontal', size_hint=(1, None))

        main_box.add_widget(settings)
        settings.add_widget(main_buttons)
        settings.add_widget(frequency_layout)
        settings.add_widget(amplitude_layout)
        box.add_widget(range_layout)
        settings.add_widget(phase_layout)
        settings.add_widget(offset_layout)
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
            Button(text='+'),
            Button(text='-'),
            Button(text='reset')
        ]
        def change_range(positive):
            if positive:
                self.parameters.ramp_amplitude.value *= 1.5
            else:
                self.parameters.ramp_amplitude.value /= 1.5
            self.control.write_data()

        def reset_range(e):
            self.parameters.ramp_amplitude.reset()
            self.parameters.center.reset()

        scan_range_buttons[0].bind(on_press=lambda e: change_range(False))
        scan_range_buttons[1].bind(on_press=lambda e: change_range(True))
        scan_range_buttons[2].bind(on_press=reset_range)

        scan_range_display = Label()
        self.parameters.ramp_amplitude.change(
            lambda value: setattr(scan_range_display, 'text', '%d %%' % (value * 100))
        )
        for element in [scan_range_display, scan_range_buttons[1], scan_range_buttons[0],scan_range_buttons[2]]:
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

        # offset input
        offset_input = NumberInput(text=str(self.parameters.offset._start), multiline=False)
        def change_offset(input):
            try:
                value = int(input.text)
            except ValueError:
                input.text = str(self.parameters.offset.value)
                return

            self.parameters.offset.value = value
            self.control.write_data()

        offset_input.bind(on_text_validate=change_offset)
        offset_layout.add_widget(offset_input)

        # center buttons
        def change_center(positive):
            delta_center = self.parameters.ramp_amplitude.value / 10
            if not positive:
                delta_center *= -1
            new_center = self.parameters.center.value + delta_center

            if np.abs(new_center + ramp_amplitude) > 1:
                new_center = np.sign(new_center) * (1 - ramp_amplitude)

            self.parameters.center.value = new_center
            self.control.write_data()

        center_buttons[0].bind(on_press=lambda e: change_center(False))
        center_buttons[1].bind(on_press=lambda e: change_center(True))

        #self.parameters.ramp_amplitude.change(lambda v: setattr(button, 'text', str(v)))
        self.parameters.to_plot.change(self.replot)

        k = TextInput(text=str(self.parameters.k._start), multiline=False)
        f = TextInput(text=str(self.parameters.f._start), multiline=False)

        def set_numeric_pid_parameter(input, parameter):
            for i in range(2):
                try:
                    parameter.value = float(input.text)
                    break
                except ValueError:
                    # reset the value
                    input.text = str(parameter.value)

            self.control.write_data()

        def set_k(input):
            set_numeric_pid_parameter(input, self.parameters.k)

        def set_f(input):
            set_numeric_pid_parameter(input, self.parameters.f)

        k.bind(on_text_validate=set_k)
        f.bind(on_text_validate=set_f)
        lock_layout.add_widget(k)
        lock_layout.add_widget(f)

        return box

    def create_graph(self):
        self.graph = Graph(x_ticks_minor=5,
            x_ticks_major=8192, y_ticks_major=500,
            y_grid_label=True, x_grid_label=False, padding=5,
            x_grid=True, y_grid=True, xmin=-0, xmax=100, ymin=-1, ymax=1)

        def to_data_coords(widget, event):
            # global coordinates
            x, y = event.x, event.y
            # coordinates relative to widget
            x, y = widget.to_widget(x, y, relative=True)
            # data coordinates
            x, y = widget.to_data(x, y)
            return x, y

        def on_click(x, y):
            print('click', x, y)

        def on_selection(x0, x):
            x0 /= self.graph.xmax
            x /= self.graph.xmax

            center = np.mean([x, x0])
            amplitude = np.abs(center - x) * 2

            center = (center - 0.5) * 2

            print('new zoom', center, amplitude)

            self.parameters.ramp_amplitude.value = amplitude
            self.parameters.center.value = center
            self.control.write_data()

        def mouse_down(widget, event):
            # check whether click is on widget
            if not widget.collide_point(event.x, event.y):
                self.touch_start = None
                return None

            x, y = to_data_coords(widget, event)

            if 0 <= x <= self.graph.xmax:
                self.touch_start = x, y, event.x, event.y
            else:
                self.touch_start = None

        def mouse_move(widget, event):
            _, _2, x0, _3 = self.touch_start
            set_selection_overlay(x0, event.x - x0)

        def set_selection_overlay(x_start, width):
            self.overlay_rect.pos = (x_start, self.graph._plot_area.pos[1])
            self.overlay_rect.size = (width, self.graph._plot_area.size[1])

        def mouse_up(widget, event):
            # mouse down was not on widget
            if self.touch_start is None:
                return

            x0, y0, _, _2 = self.touch_start
            x, y = to_data_coords(widget, event)
            xmax = self.graph.xmax

            xdiff = np.abs(x0 - x)
            if xdiff / self.graph.xmax < 0.01:
                # it was a click
                on_click(x0, y0)
            else:
                # it was a selection
                on_selection(x0, x)

            set_selection_overlay(0, 0)
            self.touch_start = None

        self.graph.bind(on_touch_down=mouse_down)
        self.graph.bind(on_touch_up=mouse_up)
        self.graph.bind(on_touch_move=mouse_move)

        self.plot = MeshLinePlot(color=[1, 0, 0, 1])
        self.control_signal = MeshLinePlot(color=[0, 1, 0, 1])
        zero_line = MeshLinePlot(color=[1,1,1,1])
        zero_line.points = [(-1, 0), (100000, 0)]
        self.graph.add_plot(self.control_signal)
        self.graph.add_plot(self.plot)
        self.graph.add_plot(zero_line)

        overlay = InstructionGroup()
        overlay.add(Color(0, 0, 1, 0.5))
        self.overlay_rect = Rectangle(pos=(0, 0), size=(0, 100))
        overlay.add(self.overlay_rect)
        self.graph.canvas.add(overlay)

        return self.graph

    def replot(self, to_plot):
        if to_plot is not None:
            error_signal = to_plot[0]
            control_signal = to_plot[1]

            self.parameters.to_plot.value = None
            self.plot.points = list(enumerate(error_signal))
            self.control_signal.points = list(enumerate([
                point / 8192 * self.plot_max
                for point in control_signal
            ]))

            self.plot_max = np.max([-1 * self.plot_min, self.plot_max, math.ceil(np.max(error_signal))])
            self.plot_min = np.min([-1 * self.plot_max, self.plot_min, math.floor(np.min(error_signal))])

            if time() - self.last_plot_rescale > 2:
                self.graph.xmax = len(error_signal)
                self.graph.ymin = math.floor(self.plot_min)
                self.graph.ymax = math.ceil(self.plot_max)

                if self.graph.ymin == self.graph.ymax:
                    self.graph.ymax += 1

                self.last_plot_rescale = time()

    def start_ramp(self):
        self.parameters.lock.value = False
        self.control.write_data()

    def start_lock(self):
        self.parameters.lock.value = True
        self.control.write_data()
