import json
import pickle
from os import path

from linien.config import N_COLORS
from linien.gui.utils_gui import color_to_hex, param2ui
from linien.gui.widgets import CustomWidget
from PyQt5 import QtGui, QtWidgets


class ViewPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui("view_panel.ui")

    def ready(self):
        self.ids.export_select_file.clicked.connect(self.do_export_select_file)
        self.ids.export_data.clicked.connect(self.do_export_data)

        self.ids.plot_line_width.setKeyboardTracking(False)
        self.ids.plot_line_width.valueChanged.connect(self.plot_line_width_changed)

        self.ids.plot_line_opacity.setKeyboardTracking(False)
        self.ids.plot_line_opacity.valueChanged.connect(self.plot_line_opacity_changed)

        self.ids.plot_fill_opacity.setKeyboardTracking(False)
        self.ids.plot_fill_opacity.valueChanged.connect(self.plot_fill_opacity_changed)

        for color_idx in range(N_COLORS):
            getattr(self.ids, "edit_color_%d" % color_idx).clicked.connect(
                lambda *args, color_idx=color_idx: self.edit_color(color_idx)
            )

    def edit_color(self, color_idx):
        param = getattr(self.parameters, "plot_color_%d" % color_idx)

        color = QtGui.QColorDialog.getColor(QtGui.QColor.fromRgb(*param.value))
        r, g, b, a = color.getRgb()
        print("set color", color_idx, color.getRgb())
        param.value = (r, g, b, a)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        param2ui(params.plot_line_width, self.ids.plot_line_width)
        param2ui(params.plot_line_opacity, self.ids.plot_line_opacity)
        param2ui(params.plot_fill_opacity, self.ids.plot_fill_opacity)

        def preview_colors(*args):
            for color_idx in range(N_COLORS):
                element = getattr(self.ids, "display_color_%d" % color_idx)
                param = getattr(self.parameters, "plot_color_%d" % color_idx)
                element.setStyleSheet("background-color: " + color_to_hex(param.value))

        for color_idx in range(N_COLORS):
            getattr(self.parameters, "plot_color_%d" % color_idx).on_change(
                preview_colors
            )

    def plot_line_width_changed(self):
        self.parameters.plot_line_width.value = self.ids.plot_line_width.value()

    def plot_line_opacity_changed(self):
        self.parameters.plot_line_opacity.value = self.ids.plot_line_opacity.value()

    def plot_fill_opacity_changed(self):
        self.parameters.plot_fill_opacity.value = self.ids.plot_fill_opacity.value()

    def do_export_select_file(self):
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
            self.export_fn = fn
            self.ids.export_select_file.setText(
                "File selected: %s" % path.split(fn)[-1]
            )
            self.ids.export_data.setEnabled(True)

    def do_export_data(self):
        fn = self.export_fn
        counter = 0

        while True:
            if counter > 0:
                name, ext = path.splitext(fn)
                fn_with_suffix = name + "-" + str(counter)
                if ext:
                    fn_with_suffix += ext
            else:
                fn_with_suffix = fn

            try:
                open(fn_with_suffix, "r")
                counter += 1
                continue
            except FileNotFoundError:
                break

        print("export data to", fn_with_suffix)

        with open(fn_with_suffix, "w") as f:
            data = dict(self.parameters)
            data["to_plot"] = pickle.loads(data["to_plot"])

            # filter out keys that are not json-able
            for k, v in list(data.items()):
                try:
                    json.dumps(v)
                except:
                    del data[k]

            json.dump(data, f)
