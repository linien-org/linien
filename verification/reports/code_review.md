# Code Review Report — ECE554 Linien Capstone
**Reviewer:** RTL Verification  
**Date:** 2026-04-02  
**Scope:** All `.sv` files in `src/`  
**Policy:** Report only — no source files were modified.

---

## Severity Legend

| Level | Meaning |
|---|---|
| **COMPILE ERROR** | Simulation/synthesis will fail to elaborate |
| **LOGIC ERROR** | Design behaves incorrectly at runtime |
| **LINT ERROR** | Violates Cummings SNUG-2000 or IEEE 1800-2017 rules; may cause subtle sim/synth bugs |
| **LINT WARNING** | Style or portability issue; does not break functionality |

---

## Summary Table

| # | File | Severity | Rule | Description |
|---|---|---|---|---|
| 1 | `top.sv` | COMPILE ERROR | SNUG-6 | `block_drive[5]` has two drivers |
| 2 | `top.sv` | COMPILE ERROR | — | `sinusoid` instantiated with `DATA_WIDTH` param it doesn't declare |
| 3 | `top.sv` | LINT WARNING | — | `sinusoid.o_done` output unconnected |
| 4 | `bram.sv` | COMPILE ERROR | — | Module name is `reg_file`; `top.sv` instantiates `bram` |
| 5 | `chirp_gen_tb.sv` | COMPILE ERROR | — | Port `i_param_add` does not exist on DUT (should be `i_param_addr`) |
| 6 | `chirp_gen_tb.sv` | COMPILE ERROR | — | Port `done` does not exist on DUT (was removed) |
| 7 | `chirp_gen_tb.sv` | LOGIC ERROR | — | `active` port never driven — voltage output always 0 |
| 8 | `chirp_gen_tb.sv` | LOGIC ERROR | — | Reset applied after params loaded, wiping them |
| 9 | `chirp_gen_tb.sv` | LINT WARNING | IEEE-RESET | `rst` uninitialized at sim start |
| 10 | `chirp_gen_tb.sv` | LINT WARNING | IEEE-LOGIC | `i_param_add` is `[4:0]` but DUT port is `[3:0]` |
| 11 | `sinusoid.sv` | LINT ERROR | IEEE-LATCH-DEFAULT | `always_comb` case missing `default:` |
| 12 | `sinusoid.sv` | LINT ERROR | IEEE-ALWAYS | Five plain `always` blocks |
| 13 | `sinusoid.sv` | LINT WARNING | — | Interface inconsistency: `i_param_addr [4:0]` vs all other blocks `[3:0]` |
| 14 | `sinusoid.sv` | LINT WARNING | — | Missing `` `default_nettype none `` |
| 15 | `sinusoid.sv` | LOGIC ERROR | — | `run_time` / `o_done` mechanism is dead — FSM never loads `params[5]` |
| 16 | `sinusoid.sv` | LINT WARNING | IEEE-LOGIC | `output wire o_done`; `wire` used for output port |
| 17 | `sinusoid.sv` | LINT WARNING | — | Arithmetic overflow risk in LUT output calculation |
| 18 | `arb_wave.sv` | LINT ERROR | IEEE-ALWAYS | Two plain `always` blocks (lines 42, 62) |
| 19 | `arb_wave.sv` | LINT WARNING | — | Missing `` `default_nettype none `` |
| 20 | `arb_wave.sv` | LOGIC ERROR | — | `active_pulse` declared and computed but never used (dead logic) |
| 21 | `arb_wave.sv` | LINT WARNING | — | Width mismatch: `i_param_addr == 3'd0` (3-bit literal vs 4-bit port) |
| 22 | `linear_ramp.sv` | LINT ERROR | IEEE-ALWAYS | Two plain `always` blocks (lines 40, 51) |
| 23 | `linear_ramp.sv` | LOGIC ERROR | — | No clamping on `o_drive_ff` — accumulator wraps silently on overflow |
| 24 | `linear_ramp.sv` | LINT WARNING | — | `case` in `always_ff` missing `default:` |
| 25 | `direct_jump.sv` | LINT WARNING | — | Missing `` `default_nettype none `` |
| 26 | `direct_jump.sv` | LINT WARNING | IEEE-LOGIC | Bare `input`/`output` ports (no `wire`/`logic`) |
| 27 | `chirp_gen.sv` | LINT WARNING | IEEE-FF | Execution `always_ff` has no negedge rst_n in sensitivity list |
| 28 | `chirp_gen.sv` | LOGIC ERROR | — | `num_params=6` in control for chirp but DUT only handles 4 params |
| 29 | `control.sv` | LINT WARNING | IEEE-COMB-IN-FF | Multi-operand arithmetic in `always_ff` RHS |

---

## Detailed Issue Descriptions

---

### Issue 1 — `top.sv:197` — COMPILE ERROR — SNUG-6: Multiple drivers on `block_drive[5]`

```sv
// Line 197:
assign block_drive[5] = 14'b0;
// Line 207:
.o_drive (block_drive[5])   // arb_wave output also drives this net
```

`block_drive` is declared `logic [V_DATA_WIDTH-1:0] block_drive [NUM_BLOCK_TYPES]`. A `logic` variable cannot be driven by both a continuous `assign` and a module output port simultaneously. This will fail elaboration under strict IEEE SV rules and produce X in most simulators.

**Fix:** Remove `assign block_drive[5] = 14'b0;` at line 197. The `arb_wave` module already drives `o_drive = 14'b0` when `~i_active`, so the intent is already handled.

---

### Issue 2 — `top.sv:184` — COMPILE ERROR — Parameter `DATA_WIDTH` passed to `sinusoid` which has none

```sv
sinusoid #(
    .DATA_WIDTH (DATA_WIDTH)   // sinusoid.sv has NO parameter DATA_WIDTH
) u_sinusoid (
```

`sinusoid.sv` declares no module parameters. Passing `.DATA_WIDTH` to it is a compile error per IEEE 1800-2017 §23.10.

**Fix:** Remove the `#(.DATA_WIDTH(DATA_WIDTH))` override from the sinusoid instantiation in `top.sv`.

---

### Issue 3 — `top.sv:193` — LINT WARNING — `sinusoid.o_done` output unconnected

`sinusoid` exports `output wire o_done` but `top.sv` does not connect it. The signal pulses when sinusoid's internal timer reaches `run_time`. See Issue 15 for why this is also a logic problem.

**Fix:** Either connect to a monitoring signal or explicitly tie-off: `.o_done()` with a note explaining the control FSM manages duration.

---

### Issue 4 — `bram.sv:28` — COMPILE ERROR — Module name mismatch

```sv
// bram.sv contains:
module reg_file #( ...

// top.sv instantiates:
bram #(.ADDR_WIDTH(...), .DATA_WIDTH(...)) fsm_reg_file ( ...
bram #(.ADDR_WIDTH(...), .DATA_WIDTH(...)) BRAM ( ...
```

The git commit "renamed fsm_reg to bram" renamed the file but did not update the module declaration inside. Elaboration will fail with "module bram not found."

**Fix:** Change `module reg_file` to `module bram` in `bram.sv`.

---

### Issue 5 & 6 — `chirp_gen_tb.sv:19,21` — COMPILE ERROR — Stale port names

```sv
chirp_gen idut(
    .clk(clk),
    .rst_n(rst),
    .i_param_add(i_param_add),   // ERROR: port is i_param_addr
    .i_param_data(i_param_data),
    .en(start),
    .voltage(voltage),
    .done(done)                   // ERROR: no done port on current DUT
);
```

The DUT has been updated: `i_param_add` → `i_param_addr`, and `done` output was removed. The TB was not kept in sync with the DUT.

**Fix:** Update the instantiation to use `.i_param_addr(...)`, remove `.done(...)`, and add the missing `.active(...)` connection.

---

### Issue 7 — `chirp_gen_tb.sv` — LOGIC ERROR — `active` port never driven

The DUT's `active` input controls whether `voltage` is driven or forced to zero:

```sv
// In chirp_gen.sv always_comb:
if (!active) voltage = '0;
```

Since the TB never drives `active`, it defaults to 0 in simulation and `voltage` will always read 0. No meaningful output is ever observed.

---

### Issue 8 — `chirp_gen_tb.sv:46–50` — LOGIC ERROR — Reset applied after params

```sv
@(posedge clk); i_param_add = 4'd3; i_param_data = 32'h00000001;  // load params
@(posedge clk); rst = 1;           // then deassert reset (active-low)
@(posedge clk); start = 1; rst = 0; // then ASSERT reset — wipes params!
```

Active-low reset means `rst=0` asserts reset and `rst=1` deasserts it. Here reset is deasserted at line 46, then re-asserted at line 50 — after params have already been loaded. The reset clears all registers (`a`, `b`, `rate`, `raterate`), making the preceding param loads useless.

The correct sequence: assert reset first → deassert reset → then load params → then assert active.

---

### Issue 11 — `sinusoid.sv:94–106` — LINT ERROR — IEEE-LATCH-DEFAULT

```sv
always_comb begin
    case (curr_state)
        2'b00: begin ... end
        2'b01: begin ... end
        // NO default: branch
    endcase
end
```

With a 2-bit state, states `2'b10` and `2'b11` have no assignment for `next_state`. The synthesizer may infer an unintended latch.

**Fix:** Add `default: next_state = 2'b00;` inside the case.

---

### Issue 12 — `sinusoid.sv` — LINT ERROR — IEEE-ALWAYS

The following blocks should be `always_ff`:

| Line | Block Purpose |
|---|---|
| 43 | Parameter loading |
| 86 | `start_ff` edge detect |
| 110 | Timer counter |
| 124 | State register |
| 129 | Phase accumulator |

**Fix:** Replace each `always @(posedge clk, negedge rst_n)` with `always_ff @(posedge clk or negedge rst_n)`.

---

### Issue 15 — `sinusoid.sv` — LOGIC ERROR — Internal run_time / o_done mechanism is dead

`sinusoid.sv` has `params[5] = run_time` and an internal timer that triggers `o_done`. However, in `control.sv`, `num_params = 6` for sinusoid, and the last parameter (param_idx = 5, which would be `run_time`) is captured as the FSM's own `dur` counter and is **never forwarded** to the sinusoid block:

```sv
// control.sv LOAD_PARAMS:
if (last_param) begin
    dur <= i_regfile_data;    // saves to FSM timer, does NOT send to sinusoid
end else begin
    o_param_addr <= param_idx;
    o_block_en   <= type_onehot;   // only sent when NOT last_param
    o_param_data <= i_regfile_data;
end
```

Consequence: `params[5]` inside sinusoid will remain 0 (reset value). `o_done` fires immediately when `timer == run_time == 0`, but since `o_done` is unconnected in `top.sv`, this has no effect. Sinusoid's duration is effectively controlled only by the FSM's `dur` counter — the sinusoid's own timing mechanism is dead code.

**Fix (design decision required):** Either remove `run_time` / `o_done` from sinusoid and rely on the FSM for timing, or add a mechanism to forward the last param to the sinusoid as well as saving it to `dur`.

---

### Issue 18 — `arb_wave.sv:42,62` — LINT ERROR — IEEE-ALWAYS

```sv
// Line 42:
always @(posedge clk, negedge rst_n) begin  // clock divider and address counter
// Line 62:
always @(posedge clk, negedge rst_n) begin  // output pipeline
```

**Fix:** Replace both with `always_ff @(posedge clk or negedge rst_n)`.

---

### Issue 20 — `arb_wave.sv:35–36` — LOGIC ERROR — Dead signal `active_pulse`

```sv
logic active_pulse;
assign active_pulse = i_active & ~active_ff;
```

`active_pulse` is computed but never referenced anywhere in the module. Unlike `linear_ramp.sv` which uses `active_pulse` to trigger a v_start load, `arb_wave` ignores it. The BRAM address counter resets unconditionally when `~i_active`. This may or may not be intentional.

**Recommendation:** Either use `active_pulse` to reset `bram_addr_r` on the rising edge of `i_active` (consistent with other blocks), or remove the dead declaration.

---

### Issue 22 — `linear_ramp.sv:40,51` — LINT ERROR — IEEE-ALWAYS

```sv
// Line 40:
always @(posedge clk, negedge rst_n) begin  // active_ff edge detect
// Line 51:
always @(posedge clk, negedge rst_n) begin  // output drive register
```

**Fix:** Replace with `always_ff @(posedge clk or negedge rst_n)`.

---

### Issue 23 — `linear_ramp.sv:55` — LOGIC ERROR — Silent overflow

```sv
o_drive_ff <= o_drive_ff + v_step;
```

`o_drive_ff` is `[13:0]` (14-bit). If the accumulated value exceeds `+8191` or drops below `-8192`, it wraps silently. Unlike `chirp_gen.sv` which clamps via an `always_comb` output stage, `linear_ramp` has no overflow protection.

**Recommendation:** Add clamping logic before the output, consistent with `chirp_gen`'s approach.

---

### Issue 28 — `chirp_gen.sv` / `control.sv` — LOGIC ERROR — Parameter count mismatch

`control.sv` comment says chirp uses 6 params: `(start_f, end_f, amplitude, dc_offset, phase_inc, duration)` — 5 forwarded to the block plus 1 saved as duration.

`chirp_gen.sv` only handles 4 parameters (`a`, `b`, `rate`, `raterate`) via a 4-case statement. Parameters at addresses 4 and 5 that the FSM sends would be silently discarded (the `default: ;` in chirp's case). The parameter semantics in the comment (`start_f, end_f, amplitude...`) do not match the actual signals in the DUT (`a, b, rate, raterate`).

This suggests either the chirp_gen DUT is incomplete relative to the design spec, or the control FSM's param count is stale documentation from an earlier version.

---

### Issue 29 — `control.sv` — LINT WARNING — IEEE-COMB-IN-FF

The datapath `always_ff` block contains multi-operand arithmetic on the RHS of `<=`:

```sv
param_idx    <= param_idx + PARAM_IDX_WIDTH'(1);
block_idx    <= block_idx + BLOCK_IDX_WIDTH'(1);
count        <= count + DATA_WIDTH'(1);
prev_v_drive <= i_init_v_drive;   // fine, direct assignment
```

Per IEEE-COMB-IN-FF guidelines, complex expressions should be broken out into `always_comb` intermediates. This is a style warning, not a functional bug, but can mask synthesis-vs-simulation discrepancies.

---

## Files With No Issues Found

| File | Notes |
|---|---|
| `delay.sv` | Clean. One minor: `always_ff` sensitivity list uses `posedge clk` only (sync reset by design). |
| `direct_jump.sv` | Functional logic correct. Missing `default_nettype none` (Issue 25). |

---

## Recommended Fix Priority

1. **Fix first (blocks compilation):** Issues 1, 2, 4, 5, 6 — nothing compiles until these are resolved.
2. **Fix before integration testing:** Issues 7, 8, 11, 15, 28 — logic errors that produce incorrect simulation results.
3. **Fix before tape-out:** Issues 12, 18, 22, 23 — IEEE-ALWAYS violations and silent overflow.
4. **Clean up as time permits:** Issues 3, 13, 14, 16, 17, 19–21, 24–27, 29.
