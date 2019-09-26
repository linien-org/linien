import json
import pickle
import numpy as np
from os import path
from PyQt5 import QtGui, QtWidgets

from linien.client.utils_gui import param2ui
from linien.client.widgets import CustomWidget


class ViewPanel(QtGui.QWidget, CustomWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_ui('view_panel.ui')

    def ready(self):
        self.ids.autoscale_y_axis.stateChanged.connect(self.autoscale_changed)
        self.ids.y_axis_limit.setKeyboardTracking(False)
        self.ids.y_axis_limit.valueChanged.connect(self.y_limits_changed)

        self.ids.export_select_file.clicked.connect(self.do_export_select_file)
        self.ids.export_data.clicked.connect(self.do_export_data)

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        def set_y_limit_inputs_enabled(autoscale):
            self.ids.y_axis_limit.setEnabled(not autoscale)
        params.autoscale_y.change(set_y_limit_inputs_enabled)
        param2ui(params.autoscale_y, self.ids.autoscale_y_axis)
        param2ui(params.y_axis_limits, self.ids.y_axis_limit)

    def autoscale_changed(self):
        self.parameters.autoscale_y.value = int(self.ids.autoscale_y_axis.checkState())

    def y_limits_changed(self):
        self.parameters.y_axis_limits.value = self.ids.y_axis_limit.value()

    def do_export_select_file(self):
        options = QtWidgets.QFileDialog.Options()
        #options |= QtWidgets.QFileDialog.DontUseNativeDialog
        default_ext = '.json'
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","JSON (*%s)" % default_ext, options=options)
        if fn:
            if not fn.endswith(default_ext):
                fn = fn + default_ext
            self.export_fn = fn
            self.ids.export_select_file.setText('File selected: %s' % path.split(fn)[-1])
            self.ids.export_data.setEnabled(True)

    def do_export_data(self):
        fn = self.export_fn
        counter = 0

        while True:
            if counter > 0:
                name, ext = path.splitext(fn)
                fn_with_suffix = name + '-' + str(counter)
                if ext:
                    fn_with_suffix += ext
            else:
                fn_with_suffix = fn

            try:
                open(fn_with_suffix, 'r')
                counter += 1
                continue
            except FileNotFoundError:
                break

        print('export data to', fn_with_suffix)

        with open(fn_with_suffix, 'w') as f:
            data = dict(self.parameters)
            data['to_plot'] = pickle.loads(data['to_plot'])

            # filter out keys that are not json-able
            for k, v in list(data.items()):
                try:
                    json.dumps(v)
                except:
                    del data[k]

            json.dump(data, f)
