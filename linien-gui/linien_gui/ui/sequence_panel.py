# sequence_panel.py
# Drop into linien-gui/linien_gui/ui/
# Adds a "Sequence" tab to the settings toolbox in the main window.

import json

from PyQt5 import QtCore, QtWidgets

CLK_HZ = 125e6
PHASE_MAX = 2**32
DAC_FULL_SCALE_V = 1.0
DAC_COUNTS = 8192
DAC_MIN = -8192
DAC_MAX = 8191

BLOCK_TYPES = {
    0: "Delay",
    1: "Linear Ramp",
    2: "Direct Jump",
    3: "Chirp",
    4: "Sinusoid",
    5: "Arb Wave",
}

UNITS = {0: "s", 1: "ms", 2: "us"}

UNIT_CONVERTERS = {
    "s": lambda s: int(round(s * CLK_HZ)),
    "ms": lambda ms: int(round(ms * 1e-3 * CLK_HZ)),
    "us": lambda us: int(round(us * 1e-6 * CLK_HZ)),
}


# Human-readable param specs per block type
# Each entry: (label, unit, converter_fn)
# converter_fn converts from display value to raw FPGA value
def v_to_c(v):
    return int(round(v / DAC_FULL_SCALE_V * DAC_COUNTS))


def s_to_cy(s):
    return int(round(s * CLK_HZ))


def ms_to_cy(ms):
    return int(round(ms * 1e-3 * CLK_HZ))


def us_to_cy(us):
    return int(round(us * 1e-6 * CLK_HZ))


def hz_to_ph(hz):
    return int(round(hz * PHASE_MAX / CLK_HZ))


def hz_to_cd(hz):
    return int(round(CLK_HZ / max(hz, 0.001)))


def raw(v):
    return int(v)


BLOCK_PARAMS = {
    0: [("Hold Voltage", "V", v_to_c), ("Duration", "time", None)],
    1: [
        ("V Start", "V", v_to_c),
        ("Step Rate", "Hz", hz_to_cd),
        ("Duration", "time", None),
    ],
    2: [("Target V", "V", v_to_c), ("Duration", "time", None)],
    3: [
        ("a", "", raw),
        ("b", "", raw),
        ("Rate", "", raw),
        ("Rate Rate", "", raw),
        ("Duration", "time", None),
    ],
    4: [
        ("V Mid", "V", v_to_c),
        ("V Amp", "V", v_to_c),
        ("V Min Cut", "V", v_to_c),
        ("V Max Cut", "V", v_to_c),
        ("Frequency", "Hz", hz_to_ph),
        ("Duration", "time", None),
    ],
    5: [("Step Rate", "Hz", hz_to_cd), ("Duration", "time", None)],
}


class BlockRow(QtWidgets.QWidget):
    """One row in the sequence table representing a single block."""

    changed = QtCore.pyqtSignal()
    delete_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = True
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # block type selector
        self.type_box = QtWidgets.QComboBox()
        for idx, name in BLOCK_TYPES.items():
            self.type_box.addItem(name, idx)
        self.type_box.setFixedWidth(100)
        layout.addWidget(self.type_box)

        # param area — rebuilt when type changes
        self.param_container = QtWidgets.QWidget()
        self.param_layout = QtWidgets.QHBoxLayout(self.param_container)
        self.param_layout.setContentsMargins(0, 0, 0, 0)
        self.param_layout.setSpacing(4)
        layout.addWidget(self.param_container)

        # inline bounds warning
        self._warn_label = QtWidgets.QLabel("")
        self._warn_label.setStyleSheet("color: red; font-size: 10px;")
        self._warn_label.setVisible(False)
        layout.addWidget(self._warn_label)
        layout.addStretch()

        # delete button
        del_btn = QtWidgets.QPushButton("✕")
        del_btn.setFixedWidth(28)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        layout.addWidget(del_btn)

        self.type_box.currentIndexChanged.connect(self._rebuild_params)
        self.changed.connect(self._check_bounds)
        self._rebuild_params()
        self._building = False

    def _rebuild_params(self):
        # clear old param widgets
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        block_type = self.type_box.currentData()
        self._spinboxes = []
        for label, unit, conv_fn in BLOCK_PARAMS.get(block_type, []):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setFixedWidth(90)

            if unit == "time":
                lbl = QtWidgets.QLabel(f"{label}:")
                lbl.setStyleSheet("font-size: 10px;")
                unit_combo = QtWidgets.QComboBox()
                unit_combo.setFixedWidth(45)
                for sym in UNITS.values():
                    unit_combo.addItem(sym, sym)
                unit_combo.setCurrentIndex(1)  # default ms
                self._apply_time_range(spin, "ms")
                unit_combo.currentIndexChanged.connect(
                    lambda _, s=spin, uc=unit_combo: self._apply_time_range(
                        s, uc.currentData()
                    )
                )
                unit_combo.currentIndexChanged.connect(self.changed.emit)
                spin.valueChanged.connect(self.changed.emit)
                self.param_layout.addWidget(lbl)
                self.param_layout.addWidget(spin)
                self.param_layout.addWidget(unit_combo)
                conv = lambda v, uc=unit_combo: UNIT_CONVERTERS[uc.currentData()](v)
            else:
                lbl = QtWidgets.QLabel(f"{label}{' (' + unit + ')' if unit else ''}:")
                lbl.setStyleSheet("font-size: 10px;")
                if unit == "V":
                    spin.setRange(-1.0, 1.0)
                    spin.setSingleStep(0.01)
                elif unit == "Hz":
                    spin.setRange(0, 100000)
                    spin.setSingleStep(1)
                    spin.setValue(10)
                else:
                    spin.setRange(-1e9, 1e9)
                    spin.setSingleStep(1)
                spin.valueChanged.connect(self.changed.emit)
                self.param_layout.addWidget(lbl)
                self.param_layout.addWidget(spin)
                conv = conv_fn

            self._spinboxes.append((spin, conv))

        if not self._building:
            self.changed.emit()

    @staticmethod
    def _apply_time_range(spin, unit):
        ranges = {
            "s": (0, 100, 0.001, 0.1),
            "ms": (0, 100000, 10, 100),
            "us": (0, 1e8, 1000, 1e5),
        }
        lo, hi, step, default = ranges.get(unit, (0, 100000, 10, 100))
        spin.setRange(lo, hi)
        spin.setSingleStep(step)
        spin.setValue(default)

    def validate(self):
        """Return list of human-readable error strings for DAC bounds violations."""
        errors = []
        block_type = self.type_box.currentData()
        vals = [spin.value() for spin, _ in self._spinboxes]

        def _vc(v):
            return int(round(v / DAC_FULL_SCALE_V * DAC_COUNTS))

        def _check_v(label, v):
            c = _vc(v)
            if not (DAC_MIN <= c <= DAC_MAX):
                errors.append(
                    f"{label} {v:+.3f} V → {c} counts (range {DAC_MIN}–{DAC_MAX})"
                )

        if block_type == 0:  # Delay
            _check_v("Hold Voltage", vals[0])

        elif block_type == 1:  # Linear Ramp — only start voltage is directly known
            _check_v("V Start", vals[0])

        elif block_type == 2:  # Direct Jump
            _check_v("Target V", vals[0])

        # block 3 (Chirp) and block 5 (Arb Wave) use raw/rate params with no
        # direct voltage representation, so static bounds checking is not possible.

        elif block_type == 4:  # Sinusoid
            v_mid, v_amp = vals[0], vals[1]
            _check_v("V Mid + V Amp", v_mid + v_amp)
            _check_v("V Mid − V Amp", v_mid - v_amp)
            _check_v("V Min Cut", vals[2])
            _check_v("V Max Cut", vals[3])

        return errors

    def _check_bounds(self):
        errors = self.validate()
        if errors:
            self._warn_label.setText("⚠ " + "  |  ".join(errors))
            self._warn_label.setVisible(True)
        else:
            self._warn_label.setVisible(False)

    def to_block_dict(self):
        block_type = self.type_box.currentData()
        raw_params = [conv(spin.value()) for spin, conv in self._spinboxes]
        return {"type": block_type, "params": raw_params}

    def from_block_dict(self, d):
        self._building = True
        idx = self.type_box.findData(d["type"])
        if idx >= 0:
            self.type_box.setCurrentIndex(idx)
            self._rebuild_params()
        for i, (spin, conv) in enumerate(self._spinboxes):
            if i < len(d["params"]):
                # reverse convert: raw → display (approximate, just for UI)
                spin.setValue(d["params"][i])
        self._building = False


class SequencePanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = None
        self.control = None
        self.parameters = None
        self._rows = []

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # title
        title = QtWidgets.QLabel("Sequence Executor")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        main_layout.addWidget(title)

        # scroll area for block rows
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)
        self._row_container = QtWidgets.QWidget()
        self._row_layout = QtWidgets.QVBoxLayout(self._row_container)
        self._row_layout.setSpacing(2)
        self._row_layout.addStretch()
        scroll.setWidget(self._row_container)
        main_layout.addWidget(scroll)

        # add block button
        add_btn = QtWidgets.QPushButton("+ Add Block")
        add_btn.clicked.connect(self._add_block)
        main_layout.addWidget(add_btn)

        # status label
        self._status = QtWidgets.QLabel("")
        self._status.setStyleSheet("color: gray; font-size: 10px;")
        main_layout.addWidget(self._status)

        # arm + send buttons
        btn_row = QtWidgets.QHBoxLayout()
        self._send_btn = QtWidgets.QPushButton("Send Sequence")
        self._send_btn.clicked.connect(self._send_sequence)
        self._send_btn.setEnabled(False)
        btn_row.addWidget(self._send_btn)

        self._arm_btn = QtWidgets.QPushButton("Arm (wait for TTL)")
        self._arm_btn.setCheckable(True)
        self._arm_btn.clicked.connect(self._toggle_arm)
        self._arm_btn.setEnabled(False)
        btn_row.addWidget(self._arm_btn)
        main_layout.addLayout(btn_row)

        # save/load
        io_row = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self._save_sequence)
        load_btn = QtWidgets.QPushButton("Load")
        load_btn.clicked.connect(self._load_sequence)
        io_row.addWidget(save_btn)
        io_row.addWidget(load_btn)
        main_layout.addLayout(io_row)

    def on_connection_established(self, app):
        self.app = app
        self.control = app.control
        self.parameters = app.parameters
        self._send_btn.setEnabled(True)
        self._arm_btn.setEnabled(True)

    def _add_block(self, block_dict=None):
        row = BlockRow()
        if block_dict:
            row.from_block_dict(block_dict)
        row.delete_requested.connect(self._remove_block)
        row.changed.connect(self._on_sequence_changed)
        # insert before the stretch
        self._row_layout.insertWidget(self._row_layout.count() - 1, row)
        self._rows.append(row)
        self._on_sequence_changed()

    def _remove_block(self, row):
        self._rows.remove(row)
        self._row_layout.removeWidget(row)
        row.deleteLater()
        self._on_sequence_changed()

    def _on_sequence_changed(self):
        n = len(self._rows)
        self._status.setText(f"{n} block{'s' if n != 1 else ''} in sequence")

    def _build_sequence(self):
        return [row.to_block_dict() for row in self._rows]

    def _send_sequence(self):
        if not self._rows:
            QtWidgets.QMessageBox.warning(self, "Empty", "Add at least one block.")
            return

        all_errors = []
        for i, row in enumerate(self._rows):
            for err in row.validate():
                all_errors.append(
                    f"Block {i + 1} ({BLOCK_TYPES[row.type_box.currentData()]}): {err}"
                )
        if all_errors:
            msg = "\n".join(all_errors)
            reply = QtWidgets.QMessageBox.warning(
                self,
                "DAC Bounds Exceeded",
                f"The following blocks exceed the DAC range [{DAC_MIN}, {DAC_MAX}]:\n\n{msg}"
                "\n\nSend anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        try:
            seq = self._build_sequence()
            self.parameters.sequence_blocks.value = seq
            self.control.write_sequence_config()
            self._status.setText(f"Sent {len(seq)} blocks ✓")
        except Exception as e:
            self._status.setText(f"Error: {e}")
            QtWidgets.QMessageBox.critical(self, "Send failed", str(e))

    def _toggle_arm(self, checked):
        if not self.control:
            return
        try:
            if checked:
                self._send_sequence()
                self._arm_btn.setText("Disarm")
                self._arm_btn.setStyleSheet("background: #00aa00;")
            else:
                # disarm by setting arm CSR to 0
                self.parameters.sequence_blocks.value = []
                self.control.write_sequence_config()
                self._arm_btn.setText("Arm (wait for TTL)")
                self._arm_btn.setStyleSheet("")
        except Exception as e:
            self._status.setText(f"Error: {e}")

    def _save_sequence(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Sequence", "", "JSON (*.json)"
        )
        if fn:
            if not fn.endswith(".json"):
                fn += ".json"
            with open(fn, "w") as f:
                json.dump(self._build_sequence(), f, indent=2)
            self._status.setText(f"Saved to {fn}")

    def _load_sequence(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Sequence", "", "JSON (*.json)"
        )
        if fn:
            with open(fn) as f:
                seq = json.load(f)
            # clear existing rows
            for row in list(self._rows):
                self._remove_block(row)
            for block in seq:
                self._add_block(block)
            self._status.setText(f"Loaded {len(seq)} blocks from {fn}")
