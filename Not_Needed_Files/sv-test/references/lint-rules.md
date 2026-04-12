# Lint Rules Reference

Full rule table for sv-test static analysis. Each rule has an ID, a grep pattern to detect violations, severity, and a fix.

---

## Cummings SNUG-2000 Rules

### SNUG-1 — Sequential logic must use nonblocking assignments

**Grep pattern:** `always_ff` block containing `\b\w+\s*=\s*` (blocking `=` that is not inside `if/case` condition)

**Detection approach:**
- Read each `always_ff` block
- Flag any `<signal> =` (blocking) that is not part of a comparison (`==`, `!=`, `<=`, `>=`)
- Exception: `for` loop index variables in simulation-only code

**Severity:** ERROR
**Fix:** Change `=` to `<=` inside `always_ff`

---

### SNUG-2 — Latches must use nonblocking assignments

**Detection:** `always_latch` block with blocking `=`
**Severity:** ERROR
**Fix:** Change to `<=`

---

### SNUG-3 — Combinational `always` must use blocking assignments

**Grep pattern:** `always_comb` block containing `\b\w+\s*<=\s*`

**Detection:** Find `<=` inside `always_comb` blocks
**Severity:** ERROR
**Fix:** Change `<=` to `=` inside `always_comb`

---

### SNUG-4 — Mixed always block → nonblocking only

**Detection:** `always` block (not `always_ff`/`always_comb`) with both clock edge and combinational sensitivity
**Severity:** WARNING (should also be upgraded to `always_ff`)
**Fix:** Split into `always_ff` + `always_comb`, or use `<=` throughout if truly mixed

---

### SNUG-5 — Never mix blocking and nonblocking in the same always block

**Detection:** Any `always` block containing both `<=` and `=` assignments to different signals
**Severity:** ERROR
**Fix:** Split into separate `always_ff` and `always_comb` blocks

---

### SNUG-6 — Never assign the same variable from more than one always block

**Detection approach:**
1. Collect all `always_ff`, `always_comb`, `always_latch`, `always` blocks
2. Build a map: `signal_name → list of always blocks that drive it`
3. Flag any signal with more than one driver (excluding continuous `assign`)

**Severity:** ERROR (race condition)
**Fix:** Consolidate all assignments to that signal into a single always block

---

### SNUG-7 — Use `$strobe` not `$display` for nonblocking-assigned signals in TB

**Grep pattern:** `\$display.*\b(signal_driven_by_nb)\b`

**Detection:** In testbenches, find `$display` calls immediately after a nonblocking event
**Severity:** WARNING (simulation-only, but can cause misleading TB output)
**Fix:** Replace `$display` with `$strobe` for post-NBA queue values

---

### SNUG-8 — Never use `#0` delays

**Grep pattern:** `#0\b`

**Detection:** Any occurrence of `#0` in RTL or TB
**Severity:** ERROR in RTL, WARNING in TB
**Fix:** Remove `#0`; fix the underlying race condition with nonblocking assignments

---

## IEEE 1800-2017 Rules

### IEEE-ALWAYS — No plain `always` in synthesizable RTL

**Grep pattern:** `^\s*always\s+@` (not followed by `_ff`, `_comb`, `_latch`)

**Severity:** ERROR
**Fix:** Replace with `always_ff`, `always_comb`, or `always_latch` as appropriate

---

### IEEE-FF — `always_ff` must have proper clock + async reset sensitivity

**Detection:** `always_ff` without `posedge clk` or with only `posedge clk` and no reset
**Severity:** WARNING (no reset is a design choice, flag for review)
**Expected pattern:** `always_ff @(posedge clk or negedge rst_n)`

---

### IEEE-LOGIC — No `reg` or `wire` declarations

**Grep patterns:** `\breg\b`, `\bwire\b`

**Severity:** WARNING
**Fix:** Replace with `logic`; for nets that must be `wire` (e.g., tri-state), document explicitly

---

### IEEE-PARAM — Derived parameters must be `localparam`

**Detection:** `parameter` declaration whose value is a `$clog2()` expression or arithmetic on another parameter
**Severity:** ERROR
**Fix:** Change `parameter` to `localparam` for derived values

---

### IEEE-LATCH-DEFAULT — `always_comb` must assign defaults before branching

**Detection approach:**
1. Find all `always_comb` blocks
2. For each output signal assigned inside an `if`/`case`, verify it is also assigned unconditionally at the top of the block before the branch
3. Look for any `case` statement without a `default:` branch

**Severity:** ERROR (infers unintended latch)
**Fix:** Add `signal = <default>;` at top of `always_comb` and `default:` in every `case`

---

### IEEE-COMB-IN-FF — No inline combinational computation inside `always_ff`

**Detection:** Expressions with operators (`&`, `|`, `+`, `?:`, etc.) on the RHS of `<=` inside `always_ff` that reference more than one signal

**Severity:** WARNING (not illegal, but violates the intermediate signal guideline)
**Fix:** Extract to a named `logic` signal computed in `always_comb`

---

### IEEE-RESET — Active-low reset naming and polarity

**Detection:**
- Reset signal not named `rst_n` (or `*_n` suffix) → WARNING
- `if (rst_n)` instead of `if (!rst_n)` in active-low reset check → ERROR
- Reset assigned `1` instead of `'0` → ERROR

**Severity:** ERROR for polarity, WARNING for naming
**Fix:** Use `if (!rst_n)` and assign `'0` on reset

---

### IEEE-ENDMODULE — Module must end with `endmodule`

**Grep pattern:** Check that last non-blank line is `endmodule` (optionally `: module_name`)

**Severity:** ERROR
**Fix:** Add `endmodule`

---

### IEEE-CLOG2 — Width computation must use `$clog2`

**Detection:** Hard-coded width values in `localparam` that should be `$clog2(DEPTH)` or similar
**Severity:** WARNING
**Fix:** Replace magic numbers with `$clog2()` expressions

---

## Summary Table

| ID | Category | Severity | Key Pattern |
|---|---|---|---|
| SNUG-1 | Sequential blocking | ERROR | `=` in `always_ff` |
| SNUG-2 | Latch blocking | ERROR | `=` in `always_latch` |
| SNUG-3 | Comb nonblocking | ERROR | `<=` in `always_comb` |
| SNUG-4 | Mixed always | WARNING | Plain `always` with mixed sensitivity |
| SNUG-5 | Mixed assignments | ERROR | Both `=` and `<=` in same block |
| SNUG-6 | Multiple drivers | ERROR | Same signal in 2+ always blocks |
| SNUG-7 | $display vs $strobe | WARNING | `$display` after nonblocking event |
| SNUG-8 | #0 delay | ERROR/WARN | `#0` anywhere |
| IEEE-ALWAYS | Plain always | ERROR | `always @(` not `_ff/_comb/_latch` |
| IEEE-FF | FF sensitivity | WARNING | Missing reset in always_ff |
| IEEE-LOGIC | reg/wire | WARNING | `reg` or `wire` keyword |
| IEEE-PARAM | Derived param | ERROR | `parameter` with `$clog2` value |
| IEEE-LATCH-DEFAULT | Missing default | ERROR | `case` without `default:` in `always_comb` |
| IEEE-COMB-IN-FF | Inline comb in FF | WARNING | Multi-operand RHS in `<=` |
| IEEE-RESET | Reset polarity | ERROR | `if (rst_n)` instead of `if (!rst_n)` |
| IEEE-ENDMODULE | Missing endmodule | ERROR | No `endmodule` at end |
| IEEE-CLOG2 | Magic width | WARNING | Hard-coded bit widths |
