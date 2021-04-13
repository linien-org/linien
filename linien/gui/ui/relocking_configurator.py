from linien.common import (
    get_name_automatic_relocking_enabled_parameter,
    get_name_automatic_relocking_max_parameter,
    get_name_automatic_relocking_min_parameter,
)
from linien.gui.utils_gui import param2ui
from PyQt5 import QtWidgets, QtCore
from linien.gui.widgets import CustomWidget


class RelockingConfigurator(QtWidgets.QWidget, CustomWidget):
    showRelockingThresholds = QtCore.pyqtSignal(object)
    parent_relocking_tab_selected = False

    def __init__(self, *args):
        super().__init__(*args)
        self.load_ui("relocking_configurator.ui")

    def ready(self):
        self.ids.automaticRelockingCheckbox.stateChanged.connect(
            self.auto_relock_state_changed
        )

    def connection_established(self):
        params = self.app().parameters
        self.control = self.app().control
        self.parameters = params

        param2ui(params.automatic_relocking, self.ids.automaticRelockingCheckbox)

        def enable_or_disable_relocking_panel(enable):
            self.ids.automaticRelockingPanel.setEnabled(enable)

        params.automatic_relocking.on_change(enable_or_disable_relocking_panel)

        self.ids.automaticRelockingPanel.currentChanged.connect(
            self.plot_relocking_thresholds
        )

        for signal_name in ("control", "error", "monitor"):
            getattr(
                self.parameters,
                get_name_automatic_relocking_enabled_parameter(signal_name),
            ).on_change(self.plot_relocking_thresholds)
            getattr(
                self.parameters,
                get_name_automatic_relocking_max_parameter(signal_name),
            ).on_change(self.plot_relocking_thresholds)
            getattr(
                self.parameters,
                get_name_automatic_relocking_min_parameter(signal_name),
            ).on_change(self.plot_relocking_thresholds)

    def tabChanged(self, tab_index):
        """This method is called when the parent tab widget emits a change event."""
        self.parent_relocking_tab_selected = tab_index == 5
        self.plot_relocking_thresholds()

    def auto_relock_state_changed(self):
        self.parameters.automatic_relocking.value = int(
            self.ids.automaticRelockingCheckbox.checkState()
        )
        self.control.write_data()

        self.plot_relocking_thresholds()

    def plot_relocking_thresholds(self, *args):
        enabled_general = self.parent_relocking_tab_selected and int(
            self.ids.automaticRelockingCheckbox.checkState()
        )
        signal_index = self.automaticRelockingPanel.currentIndex()
        signal_names = ("control", "error", "monitor")
        signal_name = signal_names[signal_index]

        enabled = (
            enabled_general
            and getattr(
                self.parameters,
                get_name_automatic_relocking_enabled_parameter(signal_name),
            ).value
        )

        if not enabled:
            self.showRelockingThresholds.emit(False)
        else:
            min_ = getattr(
                self.parameters, get_name_automatic_relocking_min_parameter(signal_name)
            ).value
            max_ = getattr(
                self.parameters, get_name_automatic_relocking_max_parameter(signal_name)
            ).value

            self.showRelockingThresholds.emit(
                {
                    "thresholds": (min_, max_),
                    "vertical": [True, False, False][signal_index],
                }
            )
