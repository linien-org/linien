`default_nettype none
// ============================================================
// tb_arb_wave.sv — Testbench for arb_wave.sv (Block Type 5)
//
// Uses an inline BRAM model (simple array) to simulate the
// dual-port register file interface exposed by arb_wave.
//
// Compile:
//   iverilog -g2012 -Wall -o sim_awg src/arb_wave.sv verification/tb/tb_arb_wave.sv
//   vvp sim_awg
// Waveform:
//   gtkwave tb_arb_wave.vcd
// ============================================================
module tb_arb_wave;

localparam CLK_HALF = 5;

logic        clk;
logic        rst_n;
logic [3:0]  i_param_addr;
logic [31:0] i_param_data;
logic        i_en;
logic        i_active;

logic [9:0]           o_bram_addr;
logic [13:0]          i_bram_data;
logic signed [13:0]   o_drive;

// ---- DUT ----
arb_wave dut (
    .clk          (clk),
    .rst_n        (rst_n),
    .i_param_addr (i_param_addr),
    .i_param_data (i_param_data),
    .i_en         (i_en),
    .i_active     (i_active),
    .o_bram_addr  (o_bram_addr),
    .i_bram_data  (i_bram_data),
    .o_drive      (o_drive)
);

// ---- Inline BRAM model ----
// Provides synchronous read with 1-cycle latency, like the real BRAM.
// Contents: bram_mem[addr] = addr * 4 (easily verifiable).
logic [13:0] bram_mem [1024];
initial begin
    for (int i = 0; i < 1024; i++)
        bram_mem[i] = 14'(i * 4);
end

// Sync read — model the 1-cycle latency
always_ff @(posedge clk) begin
    i_bram_data <= bram_mem[o_bram_addr];
end

initial clk = 0;
always #CLK_HALF clk = ~clk;

initial begin
    $dumpfile("tb_arb_wave.vcd");
    $dumpvars(0, tb_arb_wave);
end

int pass_count = 0;
int fail_count = 0;

task check14(input string name, input logic [13:0] got, input logic [13:0] expected);
    if (got === expected) begin
        $display("  PASS [%s]: got 0x%04h (%0d)", name, got, got);
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got 0x%04h (%0d), expected 0x%04h (%0d)",
                 name, got, got, expected, expected);
        fail_count++;
    end
endtask

task check10(input string name, input logic [9:0] got, input logic [9:0] expected);
    if (got === expected) begin
        $display("  PASS [%s]: addr=%0d", name, got);
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got addr=%0d, expected %0d", name, got, expected);
        fail_count++;
    end
endtask

task do_reset(input int cycles);
    rst_n <= 0; i_en <= 0; i_active <= 0; i_param_addr <= '0; i_param_data <= '0;
    repeat (cycles) @(negedge clk);
    rst_n <= 1;
    @(negedge clk);
endtask

task load_clk_div(input logic [31:0] div);
    @(negedge clk);
    i_en <= 1; i_param_addr <= 4'd0; i_param_data <= div;
    @(negedge clk);
    i_en <= 0;
endtask

initial begin
    $display("=== tb_arb_wave: begin ===");
    rst_n = 1; i_en = 0; i_active = 0; i_param_addr = '0; i_param_data = '0;

    // ----------------------------------------------------------------
    // TC-A1: Reset — all outputs should be 0
    // ----------------------------------------------------------------
    $display("TC-A1: Reset assertion");
    do_reset(4);
    @(posedge clk); #1;
    check14("TC-A1 o_drive after reset", o_drive, 14'h0);
    check10("TC-A1 o_bram_addr after reset", o_bram_addr, 10'h0);

    // ----------------------------------------------------------------
    // TC-A2: clk_div=1, active → address increments every cycle
    //        o_drive follows bram with 1-cycle latency
    //        bram_mem[n] = n*4, so o_drive[cycle k] = bram_mem[k-1]*4
    // ----------------------------------------------------------------
    $display("TC-A2: clk_div=1, verify address increments and drive output");
    load_clk_div(32'd1);
    @(negedge clk); i_active <= 1;

    // Cycle 0: addr=0, BRAM reads mem[0]=0, but o_drive has 1-cycle latency
    @(posedge clk); #1;
    check10("TC-A2 addr cycle 0", o_bram_addr, 10'd0);

    @(posedge clk); #1;
    check10("TC-A2 addr cycle 1", o_bram_addr, 10'd1);
    check14("TC-A2 o_drive cycle 1 (mem[0]=0)", o_drive, 14'(0 * 4));

    @(posedge clk); #1;
    check10("TC-A2 addr cycle 2", o_bram_addr, 10'd2);
    check14("TC-A2 o_drive cycle 2 (mem[1]=4)", o_drive, 14'(1 * 4));

    @(posedge clk); #1;
    check10("TC-A2 addr cycle 3", o_bram_addr, 10'd3);
    check14("TC-A2 o_drive cycle 3 (mem[2]=8)", o_drive, 14'(2 * 4));

    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-A3: clk_div=4 — address advances every 4 cycles
    // ----------------------------------------------------------------
    $display("TC-A3: clk_div=4, address advances every 4 cycles");
    do_reset(2);
    load_clk_div(32'd4);
    @(negedge clk); i_active <= 1;
    // Run 16 cycles — addr should advance 4 times (0→1→2→3→4)
    repeat (4) @(posedge clk);
    @(posedge clk); #1;
    check10("TC-A3 addr after 4 div-cycles", o_bram_addr, 10'd1);  // 4 cycles at div=4 = 1 advance
    repeat (4) @(posedge clk);
    @(posedge clk); #1;
    check10("TC-A3 addr after 8 div-cycles", o_bram_addr, 10'd2);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-A4: Deassert active → o_drive=0, addr resets to 0
    // ----------------------------------------------------------------
    $display("TC-A4: Deassert active resets addr and clears output");
    do_reset(2);
    load_clk_div(32'd1);
    @(negedge clk); i_active <= 1;
    repeat (10) @(posedge clk);  // advance addr to ~10
    @(negedge clk); i_active <= 0;
    @(posedge clk); #1;
    check14("TC-A4 o_drive=0 after deassert", o_drive, 14'h0);
    check10("TC-A4 addr reset to 0", o_bram_addr, 10'd0);

    // ----------------------------------------------------------------
    // TC-A5: Address saturation at 1023 (does NOT wrap)
    // ----------------------------------------------------------------
    $display("TC-A5: Address saturates at 1023");
    do_reset(2);
    load_clk_div(32'd1);
    @(negedge clk); i_active <= 1;
    // Advance to addr 1023
    repeat (1023) @(posedge clk);
    @(posedge clk); #1;
    check10("TC-A5 addr at 1023", o_bram_addr, 10'd1023);
    // Extra cycles — should stay at 1023
    repeat (5) @(posedge clk);
    @(posedge clk); #1;
    check10("TC-A5 addr stays at 1023 (no wrap)", o_bram_addr, 10'd1023);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-A6: clk_div=0 edge case (div_counter == 0-1 = all-ones)
    //        addr should never advance since counter never reaches clk_div-1 = 0xFFFFFFFF
    // ----------------------------------------------------------------
    $display("TC-A6: clk_div=0 edge case (addr stuck at 0)");
    do_reset(2);
    load_clk_div(32'd0);
    @(negedge clk); i_active <= 1;
    repeat (10) @(posedge clk);
    @(posedge clk); #1;
    check10("TC-A6 addr stuck at 0 when clk_div=0", o_bram_addr, 10'd0);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-A7: Default clk_div=1 after reset (no explicit load)
    // ----------------------------------------------------------------
    $display("TC-A7: Default clk_div=1 after reset (advances every cycle)");
    do_reset(2);
    @(negedge clk); i_active <= 1;
    @(posedge clk); #1;
    check10("TC-A7 addr cycle 1", o_bram_addr, 10'd0);  // cycle 0 still addr=0
    @(posedge clk); #1;
    check10("TC-A7 addr cycle 2 = 1", o_bram_addr, 10'd1);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-A8: active_pulse dead code — verify no spurious glitches
    //        (active_ff and active_pulse exist but are unused)
    // ----------------------------------------------------------------
    $display("TC-A8: active_pulse (dead code) — no glitch on first active cycle");
    do_reset(2);
    load_clk_div(32'd1);
    @(negedge clk); i_active <= 1;
    @(posedge clk); #1;
    // addr should be 0 (first cycle), not jump to 1 from a spurious active_pulse effect
    check10("TC-A8 no addr jump on first cycle", o_bram_addr, 10'd0);
    @(negedge clk); i_active <= 0;

    $display("=== tb_arb_wave: %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("PASS: arb_wave block");
    else
        $fatal(1, "FAIL: arb_wave block has %0d failures", fail_count);

    $finish;
end

// Timeout — TC-A5 runs 1023+ cycles so needs generous budget
initial begin
    #500000;
    $fatal(1, "TIMEOUT: tb_arb_wave exceeded 500000 time units");
end

endmodule
`default_nettype wire
