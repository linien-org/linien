# Waveform Analysis Reference

How to analyze simulation failures using GTKWave and VCD text parsing.

---

## GTKWave Quick Start

### Launch
```bash
gtkwave <dumpfile.vcd> &
# or for FST:
gtkwave <dumpfile.fst> &
```

### Signal loading (GTKWave batch mode — scriptable)
```bash
# Create a GTKWave save file (.gtkw) programmatically, then load:
gtkwave <dumpfile.vcd> --script <savefile.gtkw> &
```

### Minimal .gtkw template
```
[timestart] 0
[size] 1600 900
[pos] 0 0
*-24.000000 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
[treeopen] TOP.
[sst_width] 250
[signals_width] 214
[sst_expanded] 1
[sst_vpaned_height] 150
TOP.tb.<dut_module>.clk
TOP.tb.<dut_module>.rst_n
TOP.tb.<dut_module>.<port1>
TOP.tb.<dut_module>.<port2>
```

Replace `<dut_module>` and port names with actual signal paths from the VCD.

---

## Headless / No Display — VCD Text Analysis

When GTKWave cannot be opened (no `$DISPLAY`), parse the VCD file directly.

### VCD file structure
```
$timescale 1ns $end
$var wire 1 ! clk $end
$var wire 1 " rst_n $end
$var wire 8 # data_in [7:0] $end
...
$dumpvars
x!
x"
x#
$end
#0            ← time 0
1!            ← clk = 1
0"            ← rst_n = 0
...
#10
0!
1"
```

### Parsing approach
1. Build symbol → signal name map from `$var` declarations
2. Walk time steps in order, tracking current value of each signal
3. For the failure window (±5 cycles of failure time), emit a table:

```
Time  | clk | rst_n | wr_en | rd_en | full | empty | count | data_in | data_out
------|-----|-------|-------|-------|------|-------|-------|---------|----------
  990 |  0  |   1   |   1   |   0   |   0  |   0   |  0x03 |  0xAB   |  0x12
 1000 |  1  |   1   |   1   |   0   |   0  |   0   |  0x04 |  0xAB   |  0x12
 1010 |  0  |   1   |   1   |   0   |   0  |   0   |  0x04 |  0xAB   |  0x12
 1020 |  1  |   1   |   1   |   0   |   0  |   0   |  0x05 |  0xAB   |  0x12   ← expected count=5, got 5 ✓
```

Mark the failing cycle with `← FAIL: expected X, got Y`.

---

## Failure Pattern Recognition

### Pattern 1 — Output stuck at X
```
Time  | data_out
 1000 |  x
 1020 |  x
```
- Memory was never written (reset clears pointers but not mem)
- OR: rd_ptr pointing to unwritten address
- Check: was `wr_en` ever asserted before first read?

### Pattern 2 — Signal one cycle late
```
Time  | wr_en | count (expected) | count (actual)
 1000 |   1   |       1          |      0    ← one cycle behind
 1020 |   0   |       1          |      1    ← updated one cycle late
```
- Cause: output is registered when it should be combinational
- Check: is `count` driven by `always_ff` directly exposed, or via `always_comb`?

### Pattern 3 — Signal glitches within a clock period
```
Time  | clk | data_out
  999 |  0  | 0xAB
 1000 |  1  | 0xCD   ← changed at clk edge
 1001 |  1  | 0xAB   ← glitched back within same cycle (delta cycle)
```
- Cause: blocking assignments in `always_ff` — delta-cycle race
- Fix: use nonblocking `<=` (SNUG-1)

### Pattern 4 — FSM stuck / no `$finish`
```
Time  | state | next_state
 9990 |  0x2  |   0x2     ← state not changing
10000 |  0x2  |   0x2
```
- Cause: `default:` missing in `case` → landed in encoded-but-unhandled state
- Or: input enabling FSM transition never driven

### Pattern 5 — Counter wraps to wrong value
```
Time  | count | DEPTH
 5000 | 0xFF  |  16   ← overflow: CNT_WIDTH too narrow
```
- Cause: `localparam CNT_WIDTH = $clog2(DEPTH)` instead of `$clog2(DEPTH+1)`
- Max representable value is `2^CNT_WIDTH - 1`; if DEPTH is a power of 2, you need `DEPTH+1` entries

### Pattern 6 — Multiple-driver X
```
Time  | signal
 1000 |  x     ← driven to conflicting values by two always blocks
```
- Grep for the signal name in all `always` blocks — SNUG-6 violation

---

## Annotating the Waveform Report

After identifying the failure pattern, produce a concise annotation:

```
WAVEFORM ANNOTATION
===================
Failure time  : 1000 ns
Failing signal: count
Expected      : 5  (after 5 writes, 0 reads)
Actual        : 4

Signal trace (±3 cycles around failure):
  T= 800: clk↑  wr_en=1  count=2→3   ✓
  T= 900: clk↑  wr_en=1  count=3→4   ✓
  T=1000: clk↑  wr_en=1  count=4→4   ✗  ← count did not increment
  T=1100: clk↑  wr_en=0  count=4     ✓

Pattern match: "Output stuck / not incrementing"
Root cause   : SNUG-6 — count_q driven by two always_ff blocks;
               second block overrides first with stale value

Fix          : Consolidate both count_q assignments into one always_ff block
```

---

## VCD Signal Path Naming

Different simulators use different hierarchy separators and top-level names:

| Simulator | Typical path |
|---|---|
| iverilog/vvp | `TOP.tb_module.dut_instance.signal` |
| Verilator | `TOP.tb_module.signal` |
| Questa/Xcelium | `sim:/tb_module/dut_instance/signal` |

When building the `.gtkw` file, use the hierarchy visible in the VCD's `$scope`/`$upscope` declarations.
