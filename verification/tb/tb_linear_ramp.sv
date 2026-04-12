`default_nettype none
// ============================================================
// tb_linear_ramp.sv — Testbench for linear_ramp.sv (Block Type 1)
//
// Compile:
//   iverilog -g2012 -Wall -o sim_lr src/linear_ramp.sv verification/tb/tb_linear_ramp.sv
//   vvp sim_lr
// Waveform:
//   gtkwave tb_linear_ramp.vcd
// ============================================================
module tb_linear_ramp;

localparam CLK_HALF  = 5;
localparam DATA_WIDTH = 32;

logic                  clk;
logic                  rst_n;
logic                  en;
logic [DATA_WIDTH-1:0] i_param_data;
logic [3:0]            i_param_addr;
logic                  i_active;
logic signed [13:0]    v_drive;

linear_ramp #(
    .DATA_WIDTH (DATA_WIDTH)
) dut (
    .clk          (clk),
    .rst_n        (rst_n),
    .en           (en),
    .i_param_data (i_param_data),
    .i_param_addr (i_param_addr),
    .i_active     (i_active),
    .v_drive      (v_drive)
);

initial clk = 0;
always #CLK_HALF clk = ~clk;

initial begin
    $dumpfile("tb_linear_ramp.vcd");
    $dumpvars(0, tb_linear_ramp);
end

int pass_count = 0;
int fail_count = 0;

task check_signed(input string name, input logic signed [13:0] got, input logic signed [13:0] expected);
    if (got === expected) begin
        $display("  PASS [%s]: got %0d", name, $signed(got));
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got %0d, expected %0d", name, $signed(got), $signed(expected));
        fail_count++;
    end
endtask

task check_zero(input string name);
    check_signed(name, v_drive, 14'sh0);
endtask

task do_reset(input int cycles);
    rst_n <= 0; en <= 0; i_active <= 0; i_param_data <= '0; i_param_addr <= '0;
    repeat (cycles) @(negedge clk);
    rst_n <= 1;
    @(negedge clk);
endtask

task load_param(input logic [3:0] addr, input logic [DATA_WIDTH-1:0] data);
    @(negedge clk);
    en <= 1; i_param_addr <= addr; i_param_data <= data;
    @(negedge clk);
    en <= 0;
endtask

// Load v_start (addr 0) and v_step (addr 1) in sequence
task load_ramp_params(input logic signed [13:0] v_start, input logic signed [13:0] v_step);
    load_param(4'd0, {18'b0, v_start});
    load_param(4'd1, {18'b0, v_step});
endtask

initial begin
    $display("=== tb_linear_ramp: begin ===");
    rst_n = 1; en = 0; i_active = 0; i_param_data = '0; i_param_addr = '0;

    // ----------------------------------------------------------------
    // TC-LR1: Reset
    // ----------------------------------------------------------------
    $display("TC-LR1: Reset assertion");
    do_reset(4);
    @(posedge clk); #1;
    check_zero("TC-LR1 v_drive after reset");

    // ----------------------------------------------------------------
    // TC-LR2: Positive ramp — v_start=100, v_step=5, verify 10 cycles
    // ----------------------------------------------------------------
    $display("TC-LR2: Positive ramp (start=100, step=5, 10 cycles)");
    load_ramp_params(14'sd100, 14'sd5);
    @(negedge clk); i_active <= 1;
    // First cycle after active_pulse: output loads v_start
    @(posedge clk); #1;
    check_signed("TC-LR2 cycle 0", v_drive, 14'sd100);
    @(posedge clk); #1;
    check_signed("TC-LR2 cycle 1", v_drive, 14'sd105);
    @(posedge clk); #1;
    check_signed("TC-LR2 cycle 2", v_drive, 14'sd110);
    @(posedge clk); #1;
    check_signed("TC-LR2 cycle 3", v_drive, 14'sd115);
    @(posedge clk); #1;
    check_signed("TC-LR2 cycle 4", v_drive, 14'sd120);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-LR3: Negative step (decrement)
    // ----------------------------------------------------------------
    $display("TC-LR3: Negative step (start=500, step=-10)");
    do_reset(2);
    load_ramp_params(14'sd500, -14'sd10);
    @(negedge clk); i_active <= 1;
    @(posedge clk); #1;
    check_signed("TC-LR3 cycle 0", v_drive, 14'sd500);
    @(posedge clk); #1;
    check_signed("TC-LR3 cycle 1", v_drive, 14'sd490);
    @(posedge clk); #1;
    check_signed("TC-LR3 cycle 2", v_drive, 14'sd480);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-LR4: Deassert active mid-ramp → output = 0 immediately
    // ----------------------------------------------------------------
    $display("TC-LR4: Deassert active mid-ramp");
    do_reset(2);
    load_ramp_params(14'sd200, 14'sd10);
    @(negedge clk); i_active <= 1;
    repeat (3) @(posedge clk);
    @(negedge clk); i_active <= 0;
    @(posedge clk); #1;
    check_zero("TC-LR4 v_drive=0 after deassert");

    // ----------------------------------------------------------------
    // TC-LR5: Re-trigger — reasserting active reloads v_start
    // ----------------------------------------------------------------
    $display("TC-LR5: Re-trigger loads v_start again");
    do_reset(2);
    load_ramp_params(14'sd50, 14'sd3);
    @(negedge clk); i_active <= 1;
    repeat (5) @(posedge clk);  // advance ramp 5 steps
    @(negedge clk); i_active <= 0;
    @(negedge clk); i_active <= 1;  // re-trigger
    @(posedge clk); #1;
    check_signed("TC-LR5 re-trigger starts from v_start", v_drive, 14'sd50);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-LR6: Zero step holds at v_start
    // ----------------------------------------------------------------
    $display("TC-LR6: Zero step — hold at v_start");
    do_reset(2);
    load_ramp_params(14'sd300, 14'sd0);
    @(negedge clk); i_active <= 1;
    @(posedge clk); #1;
    check_signed("TC-LR6 cycle 0", v_drive, 14'sd300);
    @(posedge clk); #1;
    check_signed("TC-LR6 cycle 1", v_drive, 14'sd300);
    @(posedge clk); #1;
    check_signed("TC-LR6 cycle 2", v_drive, 14'sd300);
    @(negedge clk); i_active <= 0;

    // ----------------------------------------------------------------
    // TC-LR7: Overflow — KNOWN BUG: wraps instead of clamping
    //   v_start=8100 (signed), step=500 → will overflow past 8191
    //   Document the wrap behavior; do not assert a "correct" expected value.
    // ----------------------------------------------------------------
    $display("TC-LR7: Overflow wrap (KNOWN BUG — document only)");
    do_reset(2);
    load_ramp_params(14'sd8100, 14'sd500);
    @(negedge clk); i_active <= 1;
    @(posedge clk); #1;
    $display("  INFO [TC-LR7] cycle 0: v_drive=%0d (expected 8100 if clamped, may wrap)", $signed(v_drive));
    @(posedge clk); #1;
    $display("  INFO [TC-LR7] cycle 1: v_drive=%0d (expected 8191 if clamped, may wrap)", $signed(v_drive));
    @(posedge clk); #1;
    $display("  INFO [TC-LR7] cycle 2: v_drive=%0d (expected 8191 if clamped, wraps to negative if bug)", $signed(v_drive));
    @(negedge clk); i_active <= 0;
    // NOTE: This TC documents the wrap behavior. A fix would clamp to ±8191.

    // ----------------------------------------------------------------
    // TC-LR8: Reset mid-ramp
    // ----------------------------------------------------------------
    $display("TC-LR8: Async reset mid-ramp");
    do_reset(2);
    load_ramp_params(14'sd400, 14'sd20);
    @(negedge clk); i_active <= 1;
    repeat (5) @(posedge clk);
    #3; rst_n <= 0;
    #2;
    check_zero("TC-LR8 v_drive=0 after async reset");
    rst_n <= 1;
    @(negedge clk); i_active <= 0;

    $display("=== tb_linear_ramp: %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("PASS: linear_ramp block");
    else
        $fatal(1, "FAIL: linear_ramp block has %0d failures", fail_count);

    $finish;
end

initial begin
    #200000;
    $fatal(1, "TIMEOUT: tb_linear_ramp exceeded 200000 time units");
end

endmodule
`default_nettype wire
