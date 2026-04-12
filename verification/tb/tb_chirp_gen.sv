`default_nettype none
// ============================================================
// tb_chirp_gen.sv — Corrected testbench for chirp_gen.sv (Block Type 3)
//
// Fixes vs the original chirp_gen_tb.sv:
//   - Uses correct port name i_param_addr (not i_param_add)
//   - No .done() port (removed from DUT)
//   - Drives .active() correctly
//   - Proper reset sequence: assert first, then deassert, then load params
//   - Adds waveform dump, assertions, pass/fail reporting
//
// Compile:
//   iverilog -g2012 -Wall -o sim_chirp src/chirp_gen.sv verification/tb/tb_chirp_gen.sv
//   vvp sim_chirp
// Waveform:
//   gtkwave tb_chirp_gen.vcd
// ============================================================
module tb_chirp_gen;

localparam CLK_HALF = 5;

logic        clk;
logic        rst_n;
logic [3:0]  i_param_addr;
logic [31:0] i_param_data;
logic        en;
logic        active;

logic signed [13:0] voltage;

chirp_gen dut (
    .clk          (clk),
    .rst_n        (rst_n),
    .i_param_addr (i_param_addr),
    .i_param_data (i_param_data),
    .en           (en),
    .active       (active),
    .voltage      (voltage)
);

initial clk = 0;
always #CLK_HALF clk = ~clk;

initial begin
    $dumpfile("tb_chirp_gen.vcd");
    $dumpvars(0, tb_chirp_gen);
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
    check_signed(name, voltage, 14'sh0);
endtask

task do_reset(input int cycles);
    rst_n <= 0; en <= 0; active <= 0; i_param_addr <= '0; i_param_data <= '0;
    repeat (cycles) @(negedge clk);
    rst_n <= 1;
    @(negedge clk);
endtask

// Load all 4 chirp params: a, b, rate, raterate
task load_chirp_params(
    input logic signed [31:0] a_val,
    input logic signed [31:0] b_val,
    input logic signed [31:0] rate_val,
    input logic signed [31:0] raterate_val
);
    @(negedge clk); en <= 1; i_param_addr <= 4'd0; i_param_data <= a_val;
    @(negedge clk); en <= 1; i_param_addr <= 4'd1; i_param_data <= b_val;
    @(negedge clk); en <= 1; i_param_addr <= 4'd2; i_param_data <= rate_val;
    @(negedge clk); en <= 1; i_param_addr <= 4'd3; i_param_data <= raterate_val;
    @(negedge clk); en <= 0;
endtask

// Compute expected chirp value at a given step:
//   cur_voltage[0] = a
//   cur_rate[0]    = rate
//   each cycle: cur_rate += raterate, cur_voltage += cur_rate (from previous cycle's rate)
// Returns expected clamped 14-bit signed value
function automatic logic signed [13:0] chirp_model(
    input logic signed [31:0] a_in,
    input logic signed [31:0] rate_in,
    input logic signed [31:0] raterate_in,
    input int step
);
    logic signed [31:0] cv, cr;
    cv = a_in;
    cr = rate_in;
    // Step 0 is the load cycle; step 1 is first update
    for (int i = 0; i < step; i++) begin
        cr = cr + raterate_in;
        cv = cv + cr;
    end
    // Clamp to 14-bit signed range
    if (cv > 32'sh1FFF)       chirp_model = 14'sh1FFF;
    else if (cv < -32'sh2000) chirp_model = -14'sh2000;
    else                      chirp_model = cv[13:0];
endfunction

initial begin
    $display("=== tb_chirp_gen: begin ===");
    rst_n = 1; en = 0; active = 0; i_param_addr = '0; i_param_data = '0;

    // ----------------------------------------------------------------
    // TC-C1: Reset clears all outputs
    // ----------------------------------------------------------------
    $display("TC-C1: Reset");
    do_reset(4);
    @(posedge clk); #1;
    check_zero("TC-C1 voltage after reset");

    // ----------------------------------------------------------------
    // TC-C2: Inactive — voltage must be 0 even with params loaded
    // ----------------------------------------------------------------
    $display("TC-C2: Voltage=0 when inactive");
    load_chirp_params(32'sd100, 32'sd0, 32'sd10, 32'sd1);
    @(posedge clk); #1;
    check_zero("TC-C2 voltage=0 when active=0");

    // ----------------------------------------------------------------
    // TC-C3: Nominal parabolic ramp — a=0, rate=10, raterate=1
    //   Step 0 (load):  cv=0, cr=10
    //   Step 1 (cycle 1): cr=10+1=11, cv=0+11=11
    //   Step 2 (cycle 2): cr=11+1=12, cv=11+12=23
    //   Step 3 (cycle 3): cr=12+1=13, cv=23+13=36
    // ----------------------------------------------------------------
    $display("TC-C3: Parabolic chirp (a=0, rate=10, raterate=1)");
    do_reset(2);
    load_chirp_params(32'sd0, 32'sd0, 32'sd10, 32'sd1);
    @(negedge clk); active <= 1;
    // Cycle 0: load cycle (active_pulse): cv=a=0, cr=rate=10 → voltage=0
    @(posedge clk); #1;
    check_signed("TC-C3 cycle 0", voltage, 14'sd0);
    @(posedge clk); #1;
    check_signed("TC-C3 cycle 1", voltage, chirp_model(32'sd0, 32'sd10, 32'sd1, 1));
    @(posedge clk); #1;
    check_signed("TC-C3 cycle 2", voltage, chirp_model(32'sd0, 32'sd10, 32'sd1, 2));
    @(posedge clk); #1;
    check_signed("TC-C3 cycle 3", voltage, chirp_model(32'sd0, 32'sd10, 32'sd1, 3));
    @(posedge clk); #1;
    check_signed("TC-C3 cycle 4", voltage, chirp_model(32'sd0, 32'sd10, 32'sd1, 4));
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-C4: Deassert active → voltage = 0
    // ----------------------------------------------------------------
    $display("TC-C4: Deassert active");
    @(posedge clk); #1;
    check_zero("TC-C4 voltage=0 after deassert");

    // ----------------------------------------------------------------
    // TC-C5: Clamp high — large positive a and rate
    // ----------------------------------------------------------------
    $display("TC-C5: Upper clamp (a=8000, rate=500, raterate=100)");
    do_reset(2);
    load_chirp_params(32'sd8000, 32'sd0, 32'sd500, 32'sd100);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;  // cycle 0: cv=8000 → clamped to 8191
    check_signed("TC-C5 cycle 0 clamped", voltage, 14'sh1FFF);
    @(posedge clk); #1;  // should still be clamped
    check_signed("TC-C5 cycle 1 still clamped", voltage, 14'sh1FFF);
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-C6: Clamp low — large negative a and rate
    // ----------------------------------------------------------------
    $display("TC-C6: Lower clamp (a=-8000, rate=-500, raterate=-100)");
    do_reset(2);
    load_chirp_params(-32'sd8000, 32'sd0, -32'sd500, -32'sd100);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;  // cv=-8000 → clamped to -8192
    check_signed("TC-C6 cycle 0 clamped", voltage, -14'sh2000);
    @(posedge clk); #1;
    check_signed("TC-C6 cycle 1 still clamped", voltage, -14'sh2000);
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-C7: Re-trigger — rising edge of active reloads 'a'
    // ----------------------------------------------------------------
    $display("TC-C7: Re-trigger reloads initial conditions");
    do_reset(2);
    load_chirp_params(32'sd50, 32'sd0, 32'sd5, 32'sd1);
    @(negedge clk); active <= 1;
    repeat (5) @(posedge clk);  // advance chirp
    @(negedge clk); active <= 0;
    @(negedge clk); active <= 1;  // re-trigger
    @(posedge clk); #1;
    check_signed("TC-C7 re-trigger loads a=50", voltage, 14'sd50);
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-C8: Params not accepted when en=0 (default state during active)
    // ----------------------------------------------------------------
    $display("TC-C8: Param write with en=0 has no effect");
    do_reset(2);
    load_chirp_params(32'sd100, 32'sd0, 32'sd0, 32'sd0); // rate=0, rr=0 → hold at 100
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check_signed("TC-C8 initial", voltage, 14'sd100);
    // Try to overwrite with en=0 (en must be explicitly 0 since active=1 and en=0 is normal)
    @(negedge clk);
    en <= 0; i_param_addr <= 4'd0; i_param_data <= 32'sd999;
    @(posedge clk); #1;
    check_signed("TC-C8 voltage unchanged (en=0)", voltage, 14'sd100);
    en <= 0; i_param_addr <= '0; i_param_data <= '0;
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-C9: Async reset mid-execution
    // ----------------------------------------------------------------
    $display("TC-C9: Async reset mid-execution");
    do_reset(2);
    load_chirp_params(32'sd200, 32'sd0, 32'sd20, 32'sd2);
    @(negedge clk); active <= 1;
    repeat (3) @(posedge clk);
    #3; rst_n <= 0;
    #2;
    check_zero("TC-C9 voltage=0 after async reset");
    rst_n <= 1;
    @(negedge clk); active <= 0;

    $display("=== tb_chirp_gen: %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("PASS: chirp_gen block");
    else
        $fatal(1, "FAIL: chirp_gen block has %0d failures", fail_count);

    $finish;
end

initial begin
    #500000;
    $fatal(1, "TIMEOUT: tb_chirp_gen exceeded 500000 time units");
end

endmodule
`default_nettype wire
