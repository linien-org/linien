---
name: sv-test
description: Test and verify SystemVerilog/Verilog modules. Use when the user asks to "test", "verify", "simulate", "run testbench", "check compliance", "lint", or "validate" a Verilog/SystemVerilog module or design. Handles .sv testbenches, UVM, and cocotb. Performs static lint against Cummings SNUG-2000 + IEEE 1800-2017 rules, compiles with verilator/iverilog, runs the testbench, and reports results. Uses GTKWave for waveform analysis on failures.
version: 1.0.0
---

# sv-test Skill

Verify a SystemVerilog DUT end-to-end: static lint → compile check → simulation → waveform analysis on failure.

If `$ARGUMENTS` specifies a module name or file path, use that as the DUT. Otherwise, ask the user which module to test.

---

## Phase 1 — Locate the DUT

1. If given a file path, read it directly.
2. If given a module name, search the project:
   - `Glob("**/*.sv")`, `Glob("**/*.v")` — look for `module <name>` in results
   - Use `Grep(pattern="module\\s+<name>", glob="**/*.{sv,v}")`
3. Read the DUT file fully before proceeding.

---

## Phase 2 — Static Lint (read the DUT, report violations)

Run through **every item** in `references/lint-rules.md`. Report each violation with:
- Rule ID (e.g. SNUG-3, IEEE-FF)
- Offending line number and code snippet
- Corrective action

**Severity levels:**
- `ERROR` — blocks synthesis or causes sim races (must fix before running)
- `WARNING` — style/portability issue (flag but continue)

If any `ERROR`-level violations exist, stop and report them. Do not proceed to compile until the user confirms or fixes them.

---

## Phase 3 — Locate the Testbench

Search the project for the TB paired with this DUT. See `references/toolchain.md § TB Discovery` for patterns. The TB may be:

| Format | Indicators |
|---|---|
| Plain SV TB | `module <name>_tb` or `tb_<name>`, instantiates DUT, has `$finish` |
| UVM | imports `uvm_pkg`, contains `uvm_test`, `uvm_env`, `uvm_agent` |
| cocotb | `test_*.py` or `*_test.py` with `@cocotb.test()` decorator |

Search strategy (in order):
1. Same directory as DUT — look for `*_tb.sv`, `tb_*.sv`, `*_tb.v`, `test_*.py`
2. `tb/`, `testbench/`, `sim/`, `test/`, `tests/` subdirectories
3. `Grep` for `instantiation of DUT module name` across all `.sv`/`.v`/`.py` files
4. If nothing found, tell the user and ask them to point to the TB

---

## Phase 4 — Blackbox Testing of Critical Components

Before running the full simulation, identify **critical boundary interfaces** on the DUT:

1. **Identify ports**: scan the DUT port list for:
   - All handshake pairs (`valid`/`ready`, `wr_en`/`full`, `rd_en`/`empty`)
   - Status/flag outputs (`full`, `empty`, `overflow`, `error`, `done`)
   - Data buses (`data_in`, `data_out`, `addr`, `wdata`, `rdata`)
   - Control inputs (`en`, `sel`, `mode`, `op`)

2. **Verify the TB exercises these blackbox scenarios** by reading the testbench and checking for:
   - Boundary conditions: empty-read attempt, full-write attempt, back-to-back operations
   - Reset behavior: assert reset mid-operation, check state after deassertion
   - Corner cases: simultaneous assert of opposing controls (e.g. `wr_en && rd_en` when count=1), max/min width values
   - Protocol compliance: no reads during empty, no writes during full (or overflow handling)

3. Report which critical scenarios **are covered** and which **are missing** from the TB.
   - Do NOT write new testbench code
   - Instead, note the gaps as warnings in your report so the user can add them

---

## Phase 5 — Compile

Follow `references/toolchain.md § Compile Commands` exactly.

**Priority order:**
1. Try `verilator --lint-only` (fastest, catches more warnings)
2. If verilator unavailable, try `iverilog -Wall -g2012 -o /dev/null`
3. For cocotb, check Python imports: `python3 -c "import cocotb"` first

Capture stdout + stderr. If compile fails:
- Show the full error output
- Map each error back to the lint rules if applicable
- Ask the user whether to continue or fix first

---

## Phase 6 — Run Simulation

Follow `references/toolchain.md § Run Commands`.

**Execution:**
- Set a simulation timeout (default 10 000 clock cycles or as specified in TB)
- Capture all stdout/stderr
- Note any `$dumpfile`/`$dumpvars` calls — record the VCD/FST output path
- Note any `$finish`/`$fatal` calls and the line/time they fired

**Pass/Fail detection** (in priority order):
1. Explicit: `$fatal`, `$error`, `assert ... else $fatal` in TB → FAIL
2. Explicit: `$display("PASS")` / `$display("FAIL")` patterns in TB output
3. UVM: look for `UVM_FATAL`, `UVM_ERROR` counts in report summary
4. cocotb: pytest exit code, `AssertionError` tracebacks
5. Timeout with no `$finish` → FAIL (likely hung)

---

## Phase 7 — Report Results

### On PASS

```
=== SIMULATION RESULT: PASS ===
DUT     : <module_name> (<file_path>)
Testbench: <tb_path>
Simulator: <tool + version>
Runtime  : <sim time>

Lint     : <N errors, M warnings>
Coverage : <if reported by TB>

Critical component coverage:
  [COVERED]  <port/scenario>
  [MISSING]  <port/scenario>  ← blackbox gaps (not blocking)
```

### On FAIL

```
=== SIMULATION RESULT: FAIL ===
DUT     : <module_name>
Failure : <error message / assertion / timeout>
Sim time: <time of failure>
```

Then proceed immediately to Phase 8.

---

## Phase 8 — Failure Analysis (GTKWave + VCD)

Follow `references/waveform.md` for the full analysis workflow.

**Step 1 — Confirm VCD exists**
- Check the path from `$dumpfile()` in the TB, or look for `*.vcd`, `*.fst`, `*.lxt` in the sim directory
- If no VCD: re-run simulation with `-fst` or add `$dumpvars` note to user (do not edit TB unless user asks)

**Step 2 — Open GTKWave (if display available)**
```bash
gtkwave <dumpfile.vcd> &
```
Add the following signals in GTKWave: all DUT ports, the failing signal(s), clock, reset.

**Step 3 — Textual VCD analysis (always, display or not)**
Parse the VCD file to extract signal transitions around the failure time:
- Window: 5 clock cycles before failure to 5 cycles after
- Report a signal table: time | clk | rst_n | <relevant signals>
- Identify which signal diverged from expected value

**Step 4 — Root cause classification**

| Pattern | Likely cause |
|---|---|
| Output never changes after reset | Reset not deasserted, or enable never asserted |
| Output changes one cycle late | Missing registered/combinational split; should use comb intermediate |
| Signal glitches at clock edge | Blocking assignment in `always_ff` (Cummings rule 1 violation) |
| X/Z propagation | Uninitialized memory, missing reset, undriven input |
| Deadlock / no `$finish` | FSM stuck in undefined state; check `default:` in case |
| Counter wraps unexpectedly | Width too narrow; check `localparam` sizing |
| Data corruption on simultaneous RW | Multiple drivers; check Cummings rule 6 |

**Step 5 — Diagnosis report**

```
=== FAILURE DIAGNOSIS ===
Failed signal : <name> at time <T>
Expected      : <value>
Got           : <value>

Root cause    : <classification from table above>
Location      : <DUT file>:<line>

Design issue  : <describe the RTL problem if it's in the DUT>
TB issue      : <describe if the TB stimulus is incorrect — rare>

Recommended fix (DUT):
  <specific code change with before/after snippet>
```

**Important:** Attribute the bug to the DUT first. Only flag the TB if the stimulus is provably wrong (e.g., violates the DUT's documented protocol). Do not recommend rewriting the TB.

---

## Reference Files

- `references/lint-rules.md` — full Cummings + IEEE rule table with grep patterns
- `references/toolchain.md` — compile/run commands for iverilog, verilator, cocotb, UVM
- `references/waveform.md` — GTKWave workflow and VCD parsing guide
