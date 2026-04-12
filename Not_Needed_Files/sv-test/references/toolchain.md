# Toolchain Reference

Compile and run commands for each simulator/testbench type.

---

## TB Discovery

### Search patterns (in priority order)

```
# 1. Direct name match next to DUT
tb_<module_name>.sv
<module_name>_tb.sv
tb_<module_name>.v
<module_name>_tb.v
test_<module_name>.py     # cocotb
<module_name>_test.py     # cocotb

# 2. Subdirectory search
tb/**/*.sv
tb/**/*.v
testbench/**/*.sv
sim/**/*.sv
test/**/*.sv
tests/**/*.py
```

### UVM detection
Grep for these patterns in `.sv` files:
```
import uvm_pkg::*;
`include "uvm_macros.svh"
class \w+ extends uvm_test
class \w+ extends uvm_env
class \w+ extends uvm_agent
```

### cocotb detection
Grep for these patterns in `.py` files:
```python
import cocotb
from cocotb
@cocotb.test()
```

Look for `Makefile` with `MODULE = test_<name>` and `TOPLEVEL = <dut_name>`.

---

## Environment Detection

Check tool availability before selecting simulator:

```bash
# Check verilator
verilator --version 2>/dev/null | head -1

# Check iverilog
iverilog -V 2>/dev/null | head -1

# Check cocotb
python3 -c "import cocotb; print(cocotb.__version__)" 2>/dev/null

# Check gtkwave
gtkwave --version 2>/dev/null | head -1
```

---

## Plain SV Testbench — iverilog

### Compile + link
```bash
iverilog -g2012 -Wall \
  -o sim_out \
  <dut_file.sv> <tb_file.sv> \
  [any_additional_pkg.sv]
```

**Common flags:**
- `-g2012` — SystemVerilog 2012 mode
- `-Wall` — all warnings
- `-I <include_dir>` — add include path
- `-y <lib_dir>` — library directory

### Run
```bash
vvp sim_out
```

### With VCD dump (if not already in TB)
If the TB has `$dumpfile`/`$dumpvars` already, VCD is automatic.
Do **not** modify the TB. If no dump exists, note it in the report.

---

## Plain SV Testbench — Verilator

### Lint only (fast, no simulation)
```bash
verilator --lint-only -Wall --timing \
  --top-module <dut_module> \
  <dut_file.sv>
```

### Compile to binary (requires `initial` / `$finish` in TB or a C++ harness)
```bash
verilator --binary -Wall --timing \
  --top-module <tb_module> \
  <dut_file.sv> <tb_file.sv> \
  -o sim_out \
  --Mdir obj_dir
./obj_dir/sim_out
```

**Note:** Verilator does not support all TB constructs (`fork/join`, `@(posedge clk)` in non-clocking-block contexts). If verilator fails on the TB, fall back to iverilog.

### With FST waveform output
```bash
verilator --binary --trace-fst --timing \
  --top-module <tb_module> \
  <dut_file.sv> <tb_file.sv> \
  --Mdir obj_dir
./obj_dir/V<tb_module>
```

---

## UVM Testbench

UVM requires a simulator with full SV support. Use one of:

### Xcelium (xrun) — if available
```bash
xrun -sv -uvm <files.sv> -top <top_module> -access +r
```

### Questa/ModelSim — if available
```bash
vlog -sv <files.sv>
vsim -c <top_module> -do "run -all; quit"
```

### iverilog limitation
iverilog does not support UVM out-of-the-box. Report this to the user if only iverilog is available. Suggest:
1. Using a free UVM stub library (`uvm-1.2` source)
2. Or switching to a UVM-capable simulator

### UVM pass/fail detection
Grep simulator output for:
```
UVM_FATAL :    0
UVM_ERROR :    0
# → PASS if both are 0

UVM_FATAL :    N   (N > 0)  → FAIL
UVM_ERROR :    N   (N > 0)  → FAIL
```

---

## cocotb Testbench

### Prerequisites check
```bash
python3 -c "import cocotb"       # cocotb installed?
python3 -c "import pytest"       # pytest installed?
which iverilog || which verilator # sim backend available?
```

### Run via Makefile (standard cocotb project)
```bash
# From the directory containing Makefile:
make SIM=icarus    # icarus iverilog backend
# or
make SIM=verilator
```

### Run via pytest (newer cocotb)
```bash
python3 -m pytest test_<module>.py -v
```

### cocotb pass/fail detection
- Exit code 0 → PASS
- Exit code non-zero → FAIL
- Grep output for `PASSED`, `FAILED`, `AssertionError`, `cocotb.result.TestFailure`

---

## Simulation Timeout

Always enforce a timeout to prevent infinite loops:

```bash
# iverilog/vvp: use timeout command
timeout 60s vvp sim_out

# If timeout triggers → report "FAIL: simulation timeout (possible hung FSM or missing $finish)"
```

---

## File Naming for VCD Output

After simulation, search for waveform files:
```bash
# Search in sim directory and subdirectories
Glob("**/*.vcd")
Glob("**/*.fst")
Glob("**/*.lxt")
Glob("**/*.lxt2")
```

Record the path for Phase 8 waveform analysis.
