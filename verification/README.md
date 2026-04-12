# Verification — ECE554 Linien Capstone

This folder contains all verification artifacts for the `sequence_top` waveform sequencer.  
**No source files in `src/` were modified.**

---

## Quick Start

### Step 1 — Read the code review first
```
verification/reports/code_review.md
```
There are **3 compile errors** that must be fixed before any simulation will elaborate. The report lists all 29 issues with exact line numbers and fixes.

### Step 2 — Apply the three mandatory fixes

| File | Change |
|---|---|
| `src/bram.sv:28` | `module reg_file` → `module bram` |
| `src/top.sv:197` | Remove `assign block_drive[5] = 14'b0;` |
| `src/top.sv:184` | Remove `#(.DATA_WIDTH(DATA_WIDTH))` from sinusoid instantiation |

### Step 3 — Run block-level testbenches

Each block TB is self-contained and can be compiled independently. Run from the repo root:

```bash
# Delay block
iverilog -g2012 -Wall -o sim_delay src/delay.sv verification/tb/tb_delay.sv && vvp sim_delay

# Direct Jump
iverilog -g2012 -Wall -o sim_dj src/direct_jump.sv verification/tb/tb_direct_jump.sv && vvp sim_dj

# Linear Ramp
iverilog -g2012 -Wall -o sim_lr src/linear_ramp.sv verification/tb/tb_linear_ramp.sv && vvp sim_lr

# Chirp Generator  (this REPLACES the broken src/chirp_gen_tb.sv)
iverilog -g2012 -Wall -o sim_chirp src/chirp_gen.sv verification/tb/tb_chirp_gen.sv && vvp sim_chirp

# Arb Wave
iverilog -g2012 -Wall -o sim_awg src/arb_wave.sv verification/tb/tb_arb_wave.sv && vvp sim_awg

# Control FSM  (no bram.sv dependency — uses inline register file model)
iverilog -g2012 -Wall -o sim_ctrl src/control.sv verification/tb/tb_control.sv && vvp sim_ctrl
```

### Step 4 — Run integration testbench

Requires the three mandatory fixes above. Also requires `sin_lut.memh` in the working directory (for the sinusoid module).

```bash
iverilog -g2012 -Wall -o sim_top \
    src/bram.sv src/control.sv src/delay.sv src/linear_ramp.sv \
    src/direct_jump.sv src/chirp_gen.sv src/sinusoid.sv src/arb_wave.sv \
    src/top.sv \
    verification/tb/tb_sequence_top.sv
vvp sim_top
```

### Step 5 — View waveforms

Each TB writes a `.vcd` file to the current directory:

```bash
gtkwave tb_delay.vcd &
gtkwave tb_chirp_gen.vcd &
gtkwave tb_control.vcd &
gtkwave tb_sequence_top.vcd &
```

---

## Folder Structure

```
verification/
├── README.md                  ← this file
├── reports/
│   └── code_review.md         ← static lint + logic issue list (29 issues)
├── methodology/
│   └── dv_plan.md             ← full verification methodology and test plan
└── tb/
    ├── tb_delay.sv            ← Block 0 (8 test cases)
    ├── tb_direct_jump.sv      ← Block 2 (8 test cases)
    ├── tb_linear_ramp.sv      ← Block 1 (8 test cases + overflow documentation)
    ├── tb_chirp_gen.sv        ← Block 3 (9 test cases, replaces broken original TB)
    ├── tb_arb_wave.sv         ← Block 5 with inline BRAM model (8 test cases)
    ├── tb_control.sv          ← FSM white-box test (9 test cases, inline regfile model)
    └── tb_sequence_top.sv     ← Full integration (9 test cases, X/Z watchdogs)
```

---

## Pass/Fail Convention

All TBs print:
- `PASS: <module name>` on success
- `$fatal` (simulator exits with error) on any failure

Automated regression:
```bash
for tb in sim_delay sim_dj sim_lr sim_chirp sim_awg sim_ctrl; do
    vvp $tb | grep -E "PASS|FAIL"
done
```

---

## Known Issues Not Yet Fixed

See `reports/code_review.md` for the full list. The most impactful unfixed items are:

| Issue | File | Impact |
|---|---|---|
| `linear_ramp` has no clamping | `src/linear_ramp.sv` | Output wraps instead of clamping at ±8191 |
| `sinusoid.o_done` / `run_time` dead | `src/sinusoid.sv` | Internal timer never loaded; sinusoid duration controlled only by FSM |
| `arb_wave.active_pulse` unused | `src/arb_wave.sv` | Dead code; address doesn't reset on rising active edge |
| `chirp_gen` param count mismatch | `src/chirp_gen.sv` + `src/control.sv` | Control allocates 6 params for chirp; DUT only uses 4 |
| 5x `always` → should be `always_ff` | `sinusoid.sv`, `arb_wave.sv`, `linear_ramp.sv` | IEEE-ALWAYS violations |
