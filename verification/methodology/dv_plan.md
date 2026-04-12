# Design Verification Plan — ECE554 Linien Capstone
**Design Under Verification:** `sequence_top` (TTL-triggered waveform sequencer for Linien spectroscopy)  
**Document Date:** 2026-04-07  
**Methodology Version:** 2.0

---

## 1. Overview

### 1.1 Design Intent

`sequence_top` is a programmable waveform sequencer. An ARM processor writes a sequence of "blocks" (delay, linear_ramp, direct_jump, chirp, sinusoid, arb_wave) into a dual-port BRAM register file. On a TTL trigger (`i_start`), the control FSM reads and executes each block in order, driving a 14-bit DAC output (`o_dac_drive`). When the sequence completes, `o_seq_done` pulses for one cycle.

### 1.2 Verification Goals

| Goal | Metric |
|---|---|
| All block types produce correct DAC output | Per-block output golden model match |
| Control FSM executes all state transitions correctly | 100% state reachability |
| Parameter bus correctly delivers params to each block type | All param addresses exercised |
| No X/Z propagation on DAC output during active sequences | Signal integrity check |
| Correct behavior on reset (sync and async paths) | Reset assertion at every FSM state |
| No rogue behavior on unexpected input combinations | Boundary & adversarial testing |
| Race condition freedom | Verified via nonblocking-assignment discipline + CDC checks |

---

## 2. Verification Environment Architecture

The testbench environment is modular: each sub-block has its own isolated testbench, and a top-level integration testbench exercises the fully assembled `sequence_top`.

```
verification/
├── reports/
│   └── code_review.md       ← static lint and logic issues (read first)
├── methodology/
│   └── dv_plan.md           ← this document
└── tb/
    ├── tb_delay.sv          ← Block 0 isolated test
    ├── tb_direct_jump.sv    ← Block 2 isolated test
    ├── tb_linear_ramp.sv    ← Block 1 isolated test
    ├── tb_chirp_gen.sv      ← Block 3 isolated test
    ├── tb_arb_wave.sv       ← Block 5 isolated test (with BRAM mock)
    ├── tb_control.sv        ← FSM test with inline register file model
    └── tb_sequence_top.sv   ← Full integration test
```

### 2.1 Prerequisite: Compile Error Status (as of v2.0)

**FIXED (confirmed in codebase):**
- `sinusoid.sv:44` — OOB array loop `i<6` → `i<5` ✓
- `sinusoid.sv:58` — Extra `end` keyword removed ✓
- `top.sv:191` — `.i_start` → `.i_active` on sinusoid instantiation ✓
- `chirp_gen_tb.sv` — Port names fixed (`.i_param_addr`, `.active` added, `.done` removed) ✓
- `arb_wave_tb.sv:32` — `reg_file` → `bram` ✓
- `arb_wave_tb.sv:9` — `i_param_data` width 14→32 bits ✓
- `linear_ramp.sv:49` — `o_drive_ff` unsigned→signed ✓
- `arb_wave.sv:24` — `3'd0` → `4'd0` literal width ✓
- `sinusoid_tb.sv:11` — `o_drive` unsigned→signed ✓
- `sinusoid.sv:17` — `i_param_addr` [4:0]→[3:0] to match 4-bit param bus ✓
- `arb_wave.sv` — Added `` `default_nettype none/wire `` guards ✓
- `arb_wave.sv:42,62` — `always` → `always_ff` ✓
- `sinusoid_tb.sv:18` — Added `#(.DATA_WIDTH(32))` ✓

**REMAINING OPEN ISSUES (non-blocking, document-and-proceed):**
- `sinusoid.sv:15` — `DATA_WIDTH` param declared but unused in module body (cosmetic)
- `chirp_gen.sv:20` — `b` param loaded at addr 1 but never referenced in execution (dead code, wastes 1 FSM cycle)
- Mixed sync/async reset styles across blocks (see §7.1 for verification strategy)
- `arb_wave.sv:50` — `clk_div==0` causes counter underflow hang (edge case, tested in TC-A6)

### 2.2 Toolchain

**Primary simulator:** Icarus Verilog (iverilog) — free, cross-platform, supports SV 2012.

**Compile command for block-level TBs:**
```bash
iverilog -g2012 -Wall \
    -o sim_out \
    src/<dut>.sv \
    verification/tb/tb_<dut>.sv
vvp sim_out
```

**Compile command for integration TB:**
```bash
iverilog -g2012 -Wall \
    -o sim_top \
    src/bram.sv src/control.sv src/delay.sv src/linear_ramp.sv \
    src/direct_jump.sv src/chirp_gen.sv src/sinusoid.sv src/arb_wave.sv \
    src/top.sv \
    verification/tb/tb_sequence_top.sv
vvp sim_top
```

**Note for sinusoid:** The `sinusoid` module uses `$readmemh("sin_lut.memh", sin_LUT)`. The `sin_lut.memh` file must be present in the working directory when simulating any TB that includes sinusoid.

**Waveform viewing:** GTKWave — open the `.vcd` output from any TB.
```bash
gtkwave dump.vcd &
```

---

## 3. Lint-First Policy

**Before running any simulation, perform a static lint pass** using the rules in `sv-test/references/lint-rules.md`. The current status is in `reports/code_review.md`. Do not advance to simulation until all `COMPILE ERROR` and `LINT ERROR` items are resolved.

**Quick lint check command (verilator):**
```bash
verilator --lint-only -Wall --timing src/<file>.sv
```

---

## 4. Block-Level Verification Plans

Each block TB follows this standard structure:
1. **Reset test** — assert rst_n=0, verify all outputs are 0
2. **Param load test** — drive en=1 with each valid param address, verify params are latched
3. **Nominal operation** — assert active, verify expected output sequence
4. **Boundary conditions** — zero/max/negative parameter values
5. **Inactive override** — verify output returns to 0 when active deasserts mid-operation
6. **Adversarial/race** — param write while active; simultaneous en and active

---

### 4.1 Delay Block (`delay.sv`) — Block Type 0

**DUT interface:**
- Inputs: `clk`, `rst_n`, `en`, `i_param_data[31:0]`, `i_param_addr[3:0]`, `active`
- Outputs: `v_drive[13:0]`

**Parameters:**
| param_addr | Meaning |
|---|---|
| 0 | `v_prev` — hold voltage while active |

**Test cases:**

| TC | Stimulus | Expected Result | Race/Rogue Check |
|---|---|---|---|
| TC-D1 | Reset assertion | `v_drive == 0` | — |
| TC-D2 | Load v_prev=512, active=1 | `v_drive == 14'd512` | — |
| TC-D3 | active=0 | `v_drive == 0` | — |
| TC-D4 | v_prev=0, active=1 | `v_drive == 0` | Zero-drive check |
| TC-D5 | v_prev=max(14'h3FFF), active=1 | `v_drive == 14'h3FFF` | Max-value check |
| TC-D6 | Write to invalid param_addr=1 while en=1 | `v_drive` unchanged | Addr decode check |
| TC-D7 | Reset asserted while active=1 | `v_drive == 0` | Async reset mid-operation |
| TC-D8 | Param write (en=1) while active=1 | Param updates live | Write-while-active race |

---

### 4.2 Direct Jump Block (`direct_jump.sv`) — Block Type 2

**DUT interface:** identical structure to delay.

**Test cases:** Mirror TC-D1 through TC-D8 (logic is identical to delay per module comment).

Additional test:

| TC | Stimulus | Expected Result |
|---|---|---|
| TC-J9 | i_param_data[31:14] has noise bits | Only bits [13:0] captured in v_target |

---

### 4.3 Linear Ramp Block (`linear_ramp.sv`) — Block Type 1

**Parameters:**
| param_addr | Meaning |
|---|---|
| 0 | `v_start` — initial voltage |
| 1 | `v_step` — signed increment per cycle |

**Test cases:**

| TC | Stimulus | Expected Result | Notes |
|---|---|---|---|
| TC-LR1 | Reset | `v_drive == 0` | — |
| TC-LR2 | Load v_start=100, v_step=5; active for 10 cycles | Output = 100,105,110,...,145 | Sample all 10 values |
| TC-LR3 | Negative step: v_start=500, v_step=-10 | Output decrements by 10 each cycle | — |
| TC-LR4 | Deassert active mid-ramp | `v_drive == 0` immediately | No latency |
| TC-LR5 | Reassert active | Starts again from v_start (new active_pulse) | Re-trigger check |
| TC-LR6 | v_step=0 | Output holds at v_start forever | Zero-step |
| TC-LR7 | Overflow test: v_start=8100, v_step=500 | **KNOWN BUG** — wraps at ±8192 boundary | Document wrap |
| TC-LR8 | Reset mid-ramp | Output clears to 0 | — |

---

### 4.4 Chirp Generator (`chirp_gen.sv`) — Block Type 3

**Parameters:**
| param_addr | Meaning |
|---|---|
| 0 | `a` — initial voltage (signed 32-bit) |
| 1 | `b` — (currently unused by FSM — see Issue 28) |
| 2 | `rate` — initial frequency rate |
| 3 | `raterate` — rate of change of rate (chirp coefficient) |

**Test cases:**

| TC | Stimulus | Expected Result | Notes |
|---|---|---|---|
| TC-C1 | Reset | `voltage == 0` | — |
| TC-C2 | Params: a=0, rate=10, raterate=1; active for 20 cycles | Output follows parabolic profile | Verify each cycle |
| TC-C3 | active deasserts | `voltage == 0` | — |
| TC-C4 | Clamp high: a=8000, rate=500, raterate=100 | `voltage` clamps at `14'sh1FFF` (8191) | Verify no overflow |
| TC-C5 | Clamp low: a=-8000, rate=-500, raterate=-100 | `voltage` clamps at `-14'sh2000` (-8192) | Verify no underflow |
| TC-C6 | Rising edge of active re-loads a | Starting from previous active | Re-trigger check |
| TC-C7 | Params written while active=1 | DUT ignores (en=0 during active) | Invariant check |
| TC-C8 | Reset mid-execution | All registers clear, voltage=0 | Async reset safety |

---

### 4.5 Arb Wave Block (`arb_wave.sv`) — Block Type 5

**Parameters:**
| param_addr | Meaning |
|---|---|
| 0 | `clk_div` — BRAM address increment period |

**Test cases:**

| TC | Stimulus | Expected Result | Notes |
|---|---|---|---|
| TC-A1 | Reset | `o_drive == 0`, `o_bram_addr == 0` | — |
| TC-A2 | clk_div=1; active; mock BRAM returning sequential values | `o_drive` follows BRAM output with 1-cycle latency | — |
| TC-A3 | clk_div=4; active for 40 cycles | Address advances every 4 cycles | Verify div_counter |
| TC-A4 | BRAM address wraps at 1023 | Address saturates at 1023, does not wrap to 0 | **Verify saturation behavior** |
| TC-A5 | Deassert active | `o_drive == 0`, addr resets to 0 | — |
| TC-A6 | clk_div=0 | Edge case: divider off-by-one (clk_div-1 = all-ones) | Underflow risk |
| TC-A7 | clk_div=1 (default reset value) | Increments every cycle | Default value check |
| TC-A8 | `active_pulse` monitoring | Currently unused — verify no glitch side effect | Dead code check |

---

### 4.6 Sinusoid Block (`sinusoid.sv`) — Block Type 4

**Note:** Sinusoid requires `sin_lut.memh` in the simulator working directory.  
**Note:** `o_done` / `run_time` is dead in top-level integration (see Issue 15). Testbench tests it in isolation.

**Parameters:**
| param_addr | Meaning |
|---|---|
| 0 | `v_mid` — DC offset |
| 1 | `v_amp` — amplitude scale |
| 2 | `v_min_cut` — lower clamp |
| 3 | `v_max_cut` — upper clamp |
| 4 | `phase_increment` — NCO step |

**Test cases:**

| TC | Stimulus | Expected Result | Notes |
|---|---|---|---|
| TC-S1 | Reset | All params=0, `o_drive=0` | — |
| TC-S2 | Load params; assert i_start (active_pulse) | `o_drive` follows LUT with scaling and DC offset | Verify a few key phase points |
| TC-S3 | v_min_cut / v_max_cut clamping | Output never exceeds cutoff values | Boundary test |
| TC-S4 | v_amp=0 | `o_drive == v_mid` constantly | Zero amplitude |
| TC-S5 | Large phase_increment | Faster traversal of LUT | Coarse sinusoid |
| TC-S6 | Param write while in WORK state | Params locked (state check in param-load logic) | Invariant |
| TC-S7 | Reset during WORK | Returns to IDLE, output = 0 | — |
| TC-S8 | run_time isolation | `o_done` fires at correct internal timer value (isolated TB) | Dead in top-level |

---

## 5. Control FSM Verification Plan (`control.sv`)

The control FSM is the most complex block and warrants dedicated white-box testing.

### 5.1 State Reachability

Every FSM state must be visited in at least one test:

| State | Triggered By |
|---|---|
| `IDLE` | Reset, or return from `DONE` |
| `FETCH_TYPE` | `i_start` pulse |
| `LOAD_INIT` | Always from `FETCH_TYPE` |
| `LOAD_PARAMS` | Always from `LOAD_INIT` |
| `START_BLOCK` | `last_param` reached in `LOAD_PARAMS` |
| `WAIT_DONE` | Always from `START_BLOCK` |
| `CAPTURE_VDRIVE` | `timer_flag` (count >= dur) |
| `DONE` | `last_block` in `CAPTURE_VDRIVE` |

### 5.2 FSM Test Cases

| TC | Scenario | Expected Behavior |
|---|---|---|
| TC-FSM1 | Single delay block (i_num_blocks=0) | Full state sequence, o_seq_done pulses once |
| TC-FSM2 | Two-block sequence (delay + linear_ramp) | Two full cycles, seq_done pulses after block 1 |
| TC-FSM3 | All 6 block types in sequence | Each type receives correct param_addr/param_data |
| TC-FSM4 | i_start while already active | FSM stays in current state (i_start ignored outside IDLE) |
| TC-FSM5 | Reset in WAIT_DONE state | Returns to IDLE, outputs cleared |
| TC-FSM6 | Reset in LOAD_PARAMS state | Returns to IDLE cleanly |
| TC-FSM7 | duration=1 (minimum timer) | Transitions WAIT_DONE→CAPTURE_VDRIVE after 1 cycle |
| TC-FSM8 | duration=0 | `timer_flag = (count >= 0)` — always true; verify graceful handling |
| TC-FSM9 | 16 blocks (i_num_blocks=15, max) | All 16 executed; seq_done fires after last |
| TC-FSM10 | Verify o_block_en is zero in START_BLOCK | No param bus activity during execution |
| TC-FSM11 | Verify prev_v_drive holds across blocks | DAC output does not glitch between blocks |
| TC-FSM12 | CAPTURE_VDRIVE captures active block drive | i_block_drive[cur_type] stored in prev_v_drive |

### 5.3 Parameter Bus Timing Verification

The parameter bus is a critical shared interface. Verify:

1. `o_param_addr` starts at 0 for the first param each block.
2. `o_block_en[type]` is only high during LOAD_PARAMS (not during START_BLOCK or WAIT_DONE).
3. `o_block_active[type]` is only high during START_BLOCK, WAIT_DONE, and CAPTURE_VDRIVE.
4. `o_param_data` is valid (`i_regfile_data`) in the same cycle `o_block_en` is high.
5. Exactly one bit of `o_block_en` is ever high (one-hot enforcement).

---

## 6. Integration Test Plan (`tb_sequence_top.sv`)

The top-level integration TB tests the full path: register file write → control FSM → block parameter load → execution → DAC output.

### 6.1 Integration Test Cases

| TC | Scenario | Verified Signals |
|---|---|---|
| TC-INT1 | Reset and idle state | All outputs 0, o_active=0, o_seq_done=0 |
| TC-INT2 | Single delay block: hold 1000 for 20 cycles | o_dac_drive=1000 during block, o_seq_done pulses at end |
| TC-INT3 | Delay → Linear Ramp sequence | DAC shows constant then ramping output |
| TC-INT4 | Direct Jump: jump to 2000 | DAC immediately reflects 2000 |
| TC-INT5 | Chirp block with observable parabolic ramp | DAC output verified against golden model |
| TC-INT6 | AWG block with pre-loaded BRAM data | DAC follows BRAM content |
| TC-INT7 | o_active timing: high from FETCH_TYPE through CAPTURE_VDRIVE | Verify with waveform |
| TC-INT8 | o_seq_done is exactly 1 cycle wide | Check rising and falling edges |
| TC-INT9 | Back-to-back starts (i_start immediately after o_seq_done) | Second sequence starts correctly |
| TC-INT10 | Reset mid-sequence | All outputs clear; FSM returns to IDLE |

---

## 7. Race Condition and Rogue Behavior Detection

### 7.1 Race Condition Tests

These tests specifically target timing hazards where signal ordering matters. Each test must be executed in integration (`tb_sequence_top.sv`) unless noted.

| ID | Test Name | Block | Description | Expected Behavior |
|----|-----------|-------|-------------|-------------------|
| RC-01 | Reset deassertion skew | `sequence_top` | Deassert `rst_n` asynchronously (not aligned to clk edge). Check all blocks exit reset in the same effective cycle. | No block should produce non-zero output before the FSM reaches START_BLOCK. Catch with X/Z watchdog. |
| RC-02 | Param load during active | All blocks | While a block is active (executing), assert `en` and write new params via the param bus. | sinusoid rejects (`i_active==0` guard on line 52). delay/direct_jump will accept (no guard) — verify this is intentional. chirp_gen rejects (en only during param phase). |
| RC-03 | `i_start` during active | `control` | Pulse `i_start` while FSM is in each non-IDLE state: FETCH_TYPE, LOAD_PARAMS, START_BLOCK, WAIT_DONE, CAPTURE_VDRIVE, DONE. | FSM must ignore re-trigger in ALL states except IDLE. No state corruption. |
| RC-04 | `block_active` to `block_drive` setup | `sequence_top` | Measure how many cycles after `o_block_active` asserts before `block_drive[cur_type]` stabilizes. | Combinational blocks (delay, direct_jump): stable same cycle. Registered blocks (linear_ramp, chirp, sinusoid, arb_wave): stable +1 cycle. `v_drive` must not sample stale data. |
| RC-05 | Back-to-back `duration=1` blocks | `control` | Program two consecutive blocks each with `duration=1`. Verify no glitch on `v_drive` during CAPTURE_VDRIVE→FETCH_TYPE transition. | `v_drive` must transition cleanly from block N output to `prev_v_drive` latch without X/Z or intermediate values. |
| RC-06 | Simultaneous BRAM read+write | `bram` | Write to address X from PS port while control FSM reads same address X on the same clock edge. | BRAM has write-first behavior (Xilinx inference). Read port should return OLD data (read registered, write latched). Verify deterministic behavior. |
| RC-07 | TTL edge during seq_done | `ttl_handler` | Fire TTL rising edge in the exact cycle that `o_seq_done` pulses. | TTL handler must process `seq_done` first (deassert `o_active`), then re-arm, then process the new TTL — no race between done acknowledgment and re-trigger. |
| RC-08 | Phase accumulator overflow | `sinusoid` | Set `phase_increment` to `32'hFFFF_FFFF` so `phase_accum` wraps every cycle. Check LUT index transition from 1023→0. | Output must follow LUT continuously without glitches at the wrap point. Combinational output should be clean. |
| RC-09 | Mixed reset deassertion timing | `sequence_top` | Assert reset for 10 cycles, then deassert. Verify that blocks with async reset (arb_wave, sinusoid, linear_ramp active_ff) and blocks with sync reset (delay, direct_jump, chirp_gen) all reach consistent state within 2 clock edges. | All `v_drive`/`o_drive`/`voltage` outputs must be 0 after reset. No block should produce spurious output during the 1-cycle sync/async reset skew. |
| RC-10 | `o_block_en` and `o_block_active` mutual exclusion | `control` | Continuously assert: `(o_block_en & o_block_active) == 0` at every cycle. | A block must never receive params (`en=1`) and be executing (`active=1`) in the same cycle. Violation means param bus data could corrupt live execution. |

### 7.2 Rogue Behavior Tests

These tests hunt for unintended or undefined behavior.

| ID | Test Name | Block | Description | Expected Behavior |
|----|-----------|-------|-------------|-------------------|
| RB-01 | X/Z propagation watchdog | `sequence_top` | Monitor `o_dac_drive` at every posedge clk after reset deasserts. If any bit is X or Z, `$fatal` immediately. | `o_dac_drive` must **never** be X/Z after reset. |
| RB-02 | `o_seq_done` pulse width | `control` | After FSM reaches DONE, verify `o_seq_done` is high for exactly 1 cycle then returns to 0. | Exactly 1 cycle. If stuck high, TTL handler will malfunction (won't re-arm). |
| RB-03 | `o_block_active` one-hot | `control` | At every cycle, assert `$onehot0(o_block_active)`. | Never more than 1 block active simultaneously. |
| RB-04 | `o_block_en` one-hot | `control` | At every cycle, assert `$onehot0(o_block_en)`. | Never more than 1 block receiving params simultaneously. |
| RB-05 | Block output when inactive | All blocks | When `active`/`i_active` is 0, verify `v_drive`/`o_drive`/`voltage` is exactly 0. | All inactive blocks must drive 0. Otherwise `i_block_drive[cur_type]` in control.sv picks up garbage from wrong block index. |
| RB-06 | FSM stuck state detection | `control` | Run a sequence and set a watchdog timer (100k cycles). If `o_seq_done` never fires, `$fatal`. | FSM must always reach DONE for any valid block program. |
| RB-07 | `duration == 0` | `control` | Program a block with `duration=0` in the register file. `timer_flag = (count >= 0)` is true when count=0. | **Two possibilities:** (a) FSM enters WAIT_DONE with `count=1` (from START_BLOCK), so `1>=0` is true → immediate exit. (b) If `count` starts at 0, immediate exit. Either way, no hang. Verify. |
| RB-08 | `clk_div == 0` in arb_wave | `arb_wave` | Write `clk_div=0` via param bus. Then activate. | `div_counter == clk_div - 1` becomes `div_counter == 32'hFFFF_FFFF`. Address will never increment (effectively frozen). **Known edge case** — document as accepted behavior or add guard. |
| RB-09 | Invalid block type | `control` | Write block type value 6 or 7 (only 0-5 are valid). Execute the sequence. | `type_onehot = 6'b1 << 6` → bit 6 shifts out of the 6-bit `o_block_en[5:0]`, so `o_block_en == 0`. No block receives params or activation. FSM will still count duration and reach DONE. Verify no hang and no X/Z on `v_drive`. |
| RB-10 | `i_num_blocks == 15` (max) | `control` | Program all 16 block slots with valid programs. Execute full sequence. | FSM must execute all 16 blocks in order and pulse `o_seq_done` exactly once at the end. |
| RB-11 | Sinusoid output clamp | `sinusoid` | Set `v_amp` to 8191, `v_mid` to 4000. `raw_out` will exceed `v_max_cut`. | Output must be clamped to `v_max_cut`, never exceed it. Similarly test `v_min_cut` with negative values. |
| RB-12 | Linear ramp overflow/wrap | `linear_ramp` | Set `v_start=8190`, `v_step=10`. Run for 5 cycles. | **KNOWN BEHAVIOR:** Output wraps at signed 14-bit boundary (no clamping logic exists). Document whether clamping should be added. |
| RB-13 | Chirp voltage clamp boundary | `chirp_gen` | Set params so `cur_voltage` oscillates around +8191/−8192 boundary. | Output must clamp at exactly `14'sh1FFF` (8191) / `-14'sh2000` (−8192), never exceed. Chirp has clamping logic; verify it. |
| RB-14 | `i_start` held high for multiple cycles | `control` | Assert `i_start=1` and hold it high for 10 cycles. | FSM should transition from IDLE→FETCH_TYPE on the first edge. On subsequent cycles, `i_start` is still high but FSM is no longer in IDLE, so it must be ignored. Only one sequence should execute. |
| RB-15 | All inputs zero after reset | `sequence_top` | Deassert reset, then leave all inputs at 0 for 1000 cycles. | All outputs must remain 0. FSM stays in IDLE. No spontaneous activity. |

### 7.3 Signal Integrity Rules (Continuous Assertions)

Embed these SVA assertions in the top-level testbench. They run **every cycle** and catch rogue behavior the instant it occurs:

```systemverilog
// RULE 1: o_dac_drive must never be X/Z after reset
property no_xz_on_dac;
    @(posedge clk) disable iff (!rst_n)
    !$isunknown(o_dac_drive);
endproperty
assert property (no_xz_on_dac) else $fatal(1, "X/Z on DAC output at time %0t!", $time);

// RULE 2: block_active must be one-hot or zero
property block_active_onehot0;
    @(posedge clk) disable iff (!rst_n)
    $onehot0(dut.block_active);
endproperty
assert property (block_active_onehot0) else $fatal(1, "Multiple blocks active at time %0t!", $time);

// RULE 3: block_en must be one-hot or zero
property block_en_onehot0;
    @(posedge clk) disable iff (!rst_n)
    $onehot0(dut.block_en);
endproperty
assert property (block_en_onehot0) else $fatal(1, "Multiple blocks enabled at time %0t!", $time);

// RULE 4: seq_done must be exactly 1 cycle wide
property seq_done_pulse;
    @(posedge clk) disable iff (!rst_n)
    $rose(o_seq_done) |=> !o_seq_done;
endproperty
assert property (seq_done_pulse) else $fatal(1, "seq_done stuck high at time %0t!", $time);

// RULE 5: block_en and block_active must never overlap for same block
property en_active_mutual_exclusion;
    @(posedge clk) disable iff (!rst_n)
    (dut.block_en & dut.block_active) == '0;
endproperty
assert property (en_active_mutual_exclusion) else
    $fatal(1, "block_en and block_active overlap at time %0t!", $time);

// RULE 6: o_active must be high during non-IDLE, non-DONE FSM states
property active_during_execution;
    @(posedge clk) disable iff (!rst_n)
    (dut.u_control.state inside {3'b001, 3'b010, 3'b011, 3'b100, 3'b101, 3'b110})
    |-> o_active;
endproperty
assert property (active_during_execution) else
    $fatal(1, "o_active dropped during active FSM state at time %0t!", $time);
```

### 7.4 Concurrency and Clocking Rules

All sequential blocks use `posedge clk` with active-low reset. No CDC crossings exist within `sequence_top` (single clock domain). The TTL handler has a 2-flop synchronizer for the external TTL input.

**Simulation discipline:**
- All TBs must drive inputs on `negedge clk` (or with `#1` after posedge) to avoid setup time violations.
- All `always_ff` blocks must use `<=` (non-blocking). Any blocking `=` in `always_ff` is a SNUG-1 violation.
- TB clock should use `always #5 clk = ~clk` (10ns period) to match realistic FPGA clocking.

**Reset discipline:**
- Mixed sync/async reset is a known inconsistency (see §2.1 remaining issues). The FSM gates all block activity, so the 1-cycle sync/async skew is functionally safe — but RC-09 explicitly tests this.
- All TBs should hold `rst_n=0` for at least 2 full clock cycles before deasserting.

### 7.5 Reset Style Consistency Matrix

| Module | Param Loading | Active FF | Output/Datapath | Recommendation |
|--------|--------------|-----------|-----------------|----------------|
| `delay` | Sync | N/A | Combinational | OK (FSM-gated) |
| `direct_jump` | Sync | N/A | Combinational | OK (FSM-gated) |
| `linear_ramp` | Sync | **Async** | **Async** | Inconsistent — verify with RC-09 |
| `chirp_gen` | Sync | Sync | Sync | OK (consistent) |
| `sinusoid` | **Async** | **Async** | Combinational | OK (consistent async) |
| `arb_wave` | **Async** | **Async** | **Async** | OK (consistent async) |
| `control` (state) | **Async** | N/A | Sync | Intentional split |
| `control` (datapath) | Sync | N/A | Sync | OK |

---

## 8. Signal Tracing Methodology

### 8.1 VCD Dump — Every TB

Every testbench includes:
```sv
initial begin
    $dumpfile("tb_<name>.vcd");
    $dumpvars(0, tb_<name>);
end
```

Waveforms are opened with GTKWave. Key signals to always include:
- `clk`, `rst_n`
- All DUT inputs/outputs
- Internal state registers (especially FSM state in `tb_control`)
- `o_seq_done`, `o_active` (integration TB)

### 8.2 Structured Signal Groups for Integration TB

The integration testbench (`tb_sequence_top.sv`) should dump signals in organized groups for efficient waveform analysis. Add these hierarchical dumps:

```systemverilog
initial begin
    $dumpfile("sequence_top_test.vcd");
    $dumpvars(0, tb_sequence_top);           // full hierarchy

    // GROUP 1: FSM State Machine (most important for debugging)
    $dumpvars(1, dut.u_control.state);
    $dumpvars(1, dut.u_control.next_state);
    $dumpvars(1, dut.u_control.block_idx);
    $dumpvars(1, dut.u_control.param_idx);
    $dumpvars(1, dut.u_control.cur_type);
    $dumpvars(1, dut.u_control.count);
    $dumpvars(1, dut.u_control.dur);
    $dumpvars(1, dut.u_control.timer_flag);
    $dumpvars(1, dut.u_control.last_param);
    $dumpvars(1, dut.u_control.last_block);

    // GROUP 2: Block Handshake Signals
    $dumpvars(1, dut.block_en);
    $dumpvars(1, dut.block_active);
    $dumpvars(1, dut.param_bus_addr);
    $dumpvars(1, dut.param_bus_data);

    // GROUP 3: DAC Output Path
    $dumpvars(1, dut.o_dac_drive);
    $dumpvars(1, dut.u_control.prev_v_drive);
    $dumpvars(1, dut.u_control.active_block_drive);
    $dumpvars(1, dut.u_control.type_onehot);

    // GROUP 4: Per-Block Drive Outputs (for mux debugging)
    $dumpvars(1, dut.block_drive[0]);  // delay
    $dumpvars(1, dut.block_drive[1]);  // linear_ramp
    $dumpvars(1, dut.block_drive[2]);  // direct_jump
    $dumpvars(1, dut.block_drive[3]);  // chirp_gen
    $dumpvars(1, dut.block_drive[4]);  // sinusoid
    $dumpvars(1, dut.block_drive[5]);  // arb_wave

    // GROUP 5: Register File Access
    $dumpvars(1, dut.reg_r_addr);
    $dumpvars(1, dut.reg_r_data);
end
```

### 8.3 GTKWave Save File Organization

Create a GTKWave save file (`.gtkw`) with these signal groups in this order:

| Group | Signals | Purpose |
|-------|---------|---------|
| **1. Clock/Reset** | `clk`, `rst_n` | Timing reference |
| **2. Top-Level I/O** | `i_start`, `o_seq_done`, `o_active`, `o_dac_drive` | High-level behavior |
| **3. FSM State** | `state`, `next_state`, `block_idx`, `cur_type` | State machine tracing |
| **4. Parameter Bus** | `o_block_en`, `o_param_addr`, `o_param_data` | Param delivery verification |
| **5. Execution** | `o_block_active`, `count`, `dur`, `timer_flag` | Block execution timing |
| **6. Block Outputs** | `block_drive[0]` through `block_drive[5]` | Per-block output verification |
| **7. DAC Path** | `prev_v_drive`, `active_block_drive`, `type_onehot` | Output mux debugging |

**Tip:** Color-code analog signals (`o_dac_drive`, `block_drive[*]`) as analog traces in GTKWave to visually spot glitches, clamp violations, and discontinuities between blocks.

### 8.4 Failure Root Cause Classification

When a test fails, use this diagnostic flowchart:

```
Output X/Z?
  → Check: Uninitialized signal, undriven port, or missing reset
  → Action: Trace back through the mux (active_block_drive → block_drive[cur_type] → which block?)
  → Common cause: block_active asserted before params loaded; cur_type indexes undriven block

Output stuck at 0?
  → Check: active/en signal path — is block_en or block_active ever asserted?
  → Check: Did rst_n properly deassert? (zoom into reset deassertion in VCD)
  → Common cause: FSM stuck in IDLE (i_start never arrived or was missed)

Output wrong value?
  → Check: param_bus_addr and param_bus_data during LOAD_PARAMS state
  → Check: reg_r_addr and reg_r_data — is the regfile returning the expected block config?
  → Common cause: block_base_addr calculation error; param_idx off by one

Output one cycle late?
  → Check: BRAM 1-cycle sync read latency; pipeline stages in arb_wave
  → Check: active_pulse timing (does it fire on the correct edge?)
  → Common cause: Reading regfile on FETCH_TYPE but data arrives in LOAD_INIT (by design)

FSM stuck in WAIT_DONE?
  → Check: timer_flag = (count >= dur). What is dur? What is count?
  → Check: Was dur loaded correctly in LOAD_PARAMS (last_param == true when dur was read)?
  → Common cause: dur=0 but count starts at 1 (from START_BLOCK), so 1>=0 is true — should exit. If stuck, dur was not loaded.

Sequence never completes?
  → Check: last_block = (block_idx == i_num_blocks). What is i_num_blocks?
  → Check: block_idx increments in CAPTURE_VDRIVE. Does it reach i_num_blocks?
  → Common cause: i_num_blocks set to wrong value; block_idx overflow

Glitch between blocks?
  → Check: prev_v_drive in CAPTURE_VDRIVE. Is active_block_drive stable when latched?
  → Check: Does v_drive mux switch cleanly from active_block_drive to prev_v_drive?
  → Common cause: Registered block output has 1-cycle latency; v_drive samples before output is valid
```

---

## 9. Coverage Goals

| Coverage Group | Bins / Description | Target | Measured By |
|---------------|-------------------|--------|-------------|
| **FSM state coverage** | All 8 states (IDLE through DONE) hit | 100% | `$display` on state change or VCD trace |
| **FSM transition coverage** | All legal state transitions exercised | 100% of 12 legal arcs | VCD state register transitions |
| **Block type activation** | Types 0-5 each executed at least once in integration | 100% | TC-INT9 exercises all 6 |
| **Block type sequencing** | Cross of (block N type) × (block N+1 type) for consecutive blocks | Best effort (6×6=36 combos) | Multi-block sequences |
| **Param address coverage** | Each block type × each valid param address written | 100% | Per-block TB checklists |
| **Duration value bins** | 0, 1, 2-10, 11-100, 101-1000, >1000 | All bins hit | TC-FSM7 (dur=1), TC-FSM8 (dur=0), TC-INT* |
| **`i_num_blocks` bins** | 0 (1 block), 1, 7, 14, 15 (max) | All bins hit | TC-FSM1 (0), TC-FSM9 (15) |
| **Voltage boundary crossing** | `v_drive` crosses 0, hits +8191, hits -8192 | All bins hit | Chirp clamp TCs, linear_ramp overflow TC |
| **Reset during FSM state** | Reset asserted during each of the 8 FSM states | 100% | TC-FSM5, TC-FSM6, add TC for remaining states |
| **Race condition tests** | RC-01 through RC-10 all executed | 100% | Dedicated race TCs |
| **Rogue behavior tests** | RB-01 through RB-15 all executed | 100% | Dedicated rogue TCs |
| **Continuous assertions** | Rules 1-6 (§7.3) active across ALL test cases | 0 violations | SVA `$fatal` on any violation |

---

## 10. Regression Strategy

### 10.1 Regression Order

Run the full regression in this strict order (each layer depends on the previous passing):

```
PHASE 0: STATIC ANALYSIS
  0a. verilator --lint-only -Wall --timing src/<each_file>.sv
  0b. iverilog -Wall -g2012 -o /dev/null src/*.sv  (link check)

PHASE 1: BLOCK-LEVEL ISOLATION
  1a. tb_delay.sv          → "PASS: delay block"
  1b. tb_direct_jump.sv    → "PASS: direct_jump block"
  1c. tb_linear_ramp.sv    → "PASS: linear_ramp block"
  1d. tb_chirp_gen.sv      → "PASS: chirp_gen block"
  1e. tb_arb_wave.sv       → "PASS: arb_wave block"

PHASE 2: FSM WHITE-BOX
  2a. tb_control.sv        → "PASS: control FSM"

PHASE 3: INTEGRATION
  3a. tb_sequence_top.sv   → "PASS: integration"
  3b. All SVA assertions   → 0 violations

PHASE 4: COCOTB REGRESSION (optional, requires cocotb installed)
  4a. cd test/arb_wave_tb && make
  4b. cd test/linear_ramp_tb && make
  4c. cd test/sinusoid_tb && make
```

### 10.2 Pass/Fail Detection

All SV TBs use `$display("PASS: ...")` on success and `$fatal(...)` on failure. Automated pass/fail:
```bash
vvp sim_out 2>&1 | grep -E "^(PASS|FATAL|ERROR)"
```

### 10.3 Verification Signoff Checklist

Before declaring verification complete, every item must be checked off:

- [ ] All source files compile without warnings (`iverilog -Wall -g2012`)
- [ ] All 6 block types pass unit-level tests with golden model comparison
- [ ] FSM state coverage: 100% of legal transitions exercised
- [ ] Block type coverage: all 6 types exercised in integration
- [ ] X/Z watchdog (Rule 1) passes for **all** test scenarios
- [ ] One-hot assertions (Rules 2-3) never fire across **all** test scenarios
- [ ] `o_seq_done` pulse assertion (Rule 4) never fires
- [ ] `en`/`active` mutual exclusion (Rule 5) never fires
- [ ] `o_active` during execution (Rule 6) never fires
- [ ] Reset during each of the 8 FSM states tested and verified
- [ ] Race condition tests RC-01 through RC-10 all pass
- [ ] Rogue behavior tests RB-01 through RB-15 all pass
- [ ] Voltage continuity verified across block boundaries (no glitches in VCD)
- [ ] `duration=0` and `duration=1` edge cases verified (RB-07, TC-FSM7/8)
- [ ] `i_num_blocks=0` and `i_num_blocks=15` verified (TC-FSM1, RB-10)
- [ ] Linear ramp overflow behavior documented and accepted (RB-12)
- [ ] Invalid block type (6,7) tested and verified (RB-09)
- [ ] All VCD waveforms reviewed for each block type in isolation and integration
- [ ] TTL handler end-to-end trigger→sequence→done cycle verified (Migen TB)
- [ ] BRAM simultaneous read/write behavior documented (RC-06)
