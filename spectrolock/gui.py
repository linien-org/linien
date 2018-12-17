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
from kivy.properties import ObjectProperty


def to_data_coords(widget, event):
    # global coordinates
    x, y = event.x, event.y
    # coordinates relative to widget
    x, y = widget.to_widget(x, y, relative=True)
    # data coordinates
    x, y = widget.to_data(x, y)
    return x, y


class NumberInput(TextInput):
    def __init__(self, *args, **kwargs):
        super(NumberInput, self).__init__(*args, **kwargs)

    def insert_text(self, substring, from_undo=False):
        substring = ''.join([
            sub for sub in substring
            if sub in string.digits + '-'
        ])
        return super(NumberInput, self).insert_text(substring, from_undo=from_undo)


class RootElement(FloatLayout):
    def __init__(self, parameters, control):
        self.control = control
        self.parameters = parameters

        self.last_plot_rescale = 0
        self.last_plot_data = None
        self.plot_max = 0
        self.plot_min = np.inf
        self.touch_start = None

        FloatLayout.__init__(self)

        self.init_graph()
        self.display_parameter_changes()
    
    def export_data(self):
        import json
        from time import time
        with open('data-%d.json' % time(), 'w') as f:
            json.dump(self.last_plot_data, f)

    def display_parameter_changes(self):
        MHz = 0x10000000 / 8
        self.parameters.modulation_frequency.change(
            lambda value: setattr(self.ids.frequency_display, 'text', '%.2f MHz' % (value / MHz))
        )

        self.parameters.modulation_amplitude.change(
            lambda value: setattr(self.ids.amplitude_display, 'text', '%d' % (value))
        )

        self.parameters.demodulation_phase.change(
            lambda value: setattr(self.ids.phase_display, 'text', hex(value))
        )

        self.parameters.ramp_amplitude.change(
            lambda value: setattr(self.ids.scan_range_display, 'text', '%d %%' % (value * 100))
        )

        self.parameters.to_plot.change(self.replot)

    def start_ramp(self):
        self.parameters.lock.value = False
        self.control.write_data()

    def start_lock(self):
        self.parameters.lock.value = True
        self.control.write_data()

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

    def change_offset(self, input):
        try:
            value = int(input.text)
        except ValueError:
            input.text = str(self.parameters.offset.value)
            return

        self.parameters.offset.value = value
        self.control.write_data()

    def change_center(self, positive):
        delta_center = self.parameters.ramp_amplitude.value / 10
        if not positive:
            delta_center *= -1
        new_center = self.parameters.center.value + delta_center

        if np.abs(new_center) + self.parameters.ramp_amplitude.value > 1:
            new_center = np.sign(new_center) * (1 - self.parameters.ramp_amplitude.value)

        self.parameters.center.value = new_center
        self.control.write_data()

    def set_numeric_pid_parameter(self, input, parameter):
        for i in range(2):
            try:
                parameter.value = float(input.text)
                break
            except ValueError:
                # reset the value
                input.text = str(parameter.value)

        self.control.write_data()

    def set_k(self, input):
        self.set_numeric_pid_parameter(input, self.parameters.k)

    def set_f(self, input):
        self.set_numeric_pid_parameter(input, self.parameters.f)

    def graph_on_click(self, x, y):
        center = x / self.ids.graph.xmax
        center = (center - 0.5) * 2
        center = self.parameters.center.value + \
            (center * self.parameters.ramp_amplitude.value)

        self.parameters.ramp_amplitude.value /= 2
        self.parameters.center.value = center
        print('click', center)
        self.control.write_data()

    def graph_on_selection(self, x0, x):
        x0 /= self.ids.graph.xmax
        x /= self.ids.graph.xmax

        center = np.mean([x, x0])
        amplitude = np.abs(center - x) * 2
        center = (center - 0.5) * 2

        amplitude *= self.parameters.ramp_amplitude.value
        center = self.parameters.center.value + \
            (center * self.parameters.ramp_amplitude.value)

        print('new zoom', center, amplitude)

        self.parameters.ramp_amplitude.value = amplitude
        self.parameters.center.value = center
        self.control.write_data()

    def graph_mouse_down(self, widget, event):
        # check whether click is on widget
        print('down')
        if not widget.collide_point(event.x, event.y):
            self.touch_start = None
            return None

        x, y = to_data_coords(widget, event)

        if 0 <= x <= self.ids.graph.xmax:
            self.touch_start = x, y, event.x, event.y
        else:
            self.touch_start = None

    def graph_mouse_move(self, widget, event):
        if self.touch_start is None:
            return
        _, _2, x0, _3 = self.touch_start
        self.set_selection_overlay(x0, event.x - x0)

    def set_selection_overlay(self, x_start, width):
        self.overlay_rect.pos = (x_start, self.ids.graph._plot_area.pos[1])
        self.overlay_rect.size = (width, self.ids.graph._plot_area.size[1])

    def graph_mouse_up(self, widget, event):
        # mouse down was not on widget
        if self.touch_start is None:
            return

        x0, y0, _, _2 = self.touch_start
        x, y = to_data_coords(widget, event)
        xmax = self.ids.graph.xmax

        xdiff = np.abs(x0 - x)
        if xdiff / self.ids.graph.xmax < 0.01:
            # it was a click
            self.graph_on_click(x0, y0)
        else:
            # it was a selection
            self.graph_on_selection(x0, x)

        self.set_selection_overlay(0, 0)
        self.touch_start = None

    def replot(self, to_plot):
        if to_plot is not None:
            error_signal = to_plot[0]
            self.last_plot_data = error_signal
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
                self.ids.graph.xmax = len(error_signal)
                self.ids.graph.ymin = math.floor(self.plot_min)
                self.ids.graph.ymax = math.ceil(self.plot_max)
                self.ids.graph.y_ticks_major = int(self.plot_max * 2 / 5)

                if self.ids.graph.ymin == self.ids.graph.ymax:
                    self.ids.graph.ymax += 1

                self.last_plot_rescale = time()

    def init_graph(self):
        self.plot = MeshLinePlot(color=[1, 0, 0, 1])
        self.control_signal = MeshLinePlot(color=[0, 1, 0, 1])
        zero_line = MeshLinePlot(color=[1,1,1,1])
        zero_line.points = [(-1, 0), (100000, 0)]
        self.ids.graph.add_plot(self.control_signal)
        self.ids.graph.add_plot(self.plot)
        self.ids.graph.add_plot(zero_line)

        overlay = InstructionGroup()
        overlay.add(Color(0, 0, 1, 0.5))
        self.overlay_rect = Rectangle(pos=(0, 0), size=(0, 100))
        overlay.add(self.overlay_rect)
        self.ids.graph.canvas.add(overlay)

    def change_range(self, positive):
        if positive:
            self.parameters.ramp_amplitude.value *= 1.5
        else:
            self.parameters.ramp_amplitude.value /= 1.5
        self.control.write_data()

    def reset_range(self):
        self.parameters.ramp_amplitude.reset()
        self.parameters.center.reset()
        self.control.write_data()


class PIDApp(App):
    foobar = ObjectProperty(None)

    def __init__(self, parameters, control):
        self.control = control
        self.parameters = parameters

        App.__init__(self)

    def build(self):
        return RootElement(self.parameters, self.control)