`default_nettype none
// ============================================================
// tb_delay.sv — Testbench for delay.sv (Block Type 0)
//
// Compile:
//   iverilog -g2012 -Wall -o sim_delay src/delay.sv verification/tb/tb_delay.sv
//   vvp sim_delay
// Waveform:
//   gtkwave tb_delay.vcd
// ============================================================
module tb_delay;

// ---- Parameters ----
localparam CLK_HALF = 5;   // 10 ns period
localparam DATA_WIDTH = 32;

// ---- Signals ----
logic                    clk;
logic                    rst_n;
logic                    en;
logic [DATA_WIDTH-1:0]   i_param_data;
logic [3:0]              i_param_addr;
logic                    active;
logic [13:0]             v_drive;

// ---- DUT ----
delay #(
    .DATA_WIDTH (DATA_WIDTH)
) dut (
    .clk          (clk),
    .rst_n        (rst_n),
    .en           (en),
    .i_param_data (i_param_data),
    .i_param_addr (i_param_addr),
    .active       (active),
    .v_drive      (v_drive)
);

// ---- Clock ----
initial clk = 0;
always #CLK_HALF clk = ~clk;

// ---- Waveform dump ----
initial begin
    $dumpfile("tb_delay.vcd");
    $dumpvars(0, tb_delay);
end

// ---- Helper tasks ----
task drive_defaults;
    en           <= 0;
    i_param_data <= '0;
    i_param_addr <= '0;
    active       <= 0;
endtask

task do_reset(input int cycles);
    rst_n <= 0;
    repeat (cycles) @(negedge clk);
    rst_n <= 1;
    @(negedge clk);
endtask

// Load a single parameter (drive on negedge to avoid setup races)
task load_param(input logic [3:0] addr, input logic [DATA_WIDTH-1:0] data);
    @(negedge clk);
    en           <= 1;
    i_param_addr <= addr;
    i_param_data <= data;
    @(negedge clk);
    en <= 0;
endtask

// ---- Pass/fail tracking ----
int pass_count = 0;
int fail_count = 0;

task check(input string name, input logic [13:0] got, input logic [13:0] expected);
    if (got === expected) begin
        $display("  PASS [%s]: got 0x%04h", name, got);
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got 0x%04h, expected 0x%04h", name, got, expected);
        fail_count++;
    end
endtask

task check_zero(input string name, input logic [13:0] got);
    check(name, got, 14'h0);
endtask

// ---- Test stimulus ----
initial begin
    $display("=== tb_delay: begin ===");

    // Initialise
    rst_n        = 1;
    drive_defaults();

    // ----------------------------------------------------------------
    // TC-D1: Reset clears v_drive
    // ----------------------------------------------------------------
    $display("TC-D1: Reset assertion");
    @(negedge clk);
    do_reset(4);
    @(posedge clk); #1;
    check_zero("TC-D1 v_drive after reset", v_drive);

    // ----------------------------------------------------------------
    // TC-D2: Load v_prev=512, assert active, check output
    // ----------------------------------------------------------------
    $display("TC-D2: Nominal hold voltage");
    load_param(4'd0, 32'd512);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-D2 v_drive=512", v_drive, 14'd512);

    // ----------------------------------------------------------------
    // TC-D3: Deassert active → output must go to 0
    // ----------------------------------------------------------------
    $display("TC-D3: Deassert active");
    @(negedge clk); active <= 0;
    @(posedge clk); #1;
    check_zero("TC-D3 v_drive=0 when inactive", v_drive);

    // ----------------------------------------------------------------
    // TC-D4: v_prev=0, active=1 → output stays 0
    // ----------------------------------------------------------------
    $display("TC-D4: Zero hold voltage");
    load_param(4'd0, 32'd0);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check_zero("TC-D4 v_drive=0 with zero param", v_drive);
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-D5: Maximum value (14-bit: 0x3FFF = 16383)
    // ----------------------------------------------------------------
    $display("TC-D5: Max hold voltage (14-bit = 16383)");
    load_param(4'd0, 32'h0000_3FFF);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-D5 v_drive=max", v_drive, 14'h3FFF);
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-D6: Write to invalid param address (addr=1) — should be ignored
    // ----------------------------------------------------------------
    $display("TC-D6: Invalid param address ignored");
    load_param(4'd0, 32'd999);     // valid write first
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-D6 pre-invalid-write value", v_drive, 14'd999);
    load_param(4'd1, 32'd0);       // write to invalid addr
    @(posedge clk); #1;
    check("TC-D6 v_drive unchanged after invalid addr write", v_drive, 14'd999);
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-D7: Async reset mid-operation
    // ----------------------------------------------------------------
    $display("TC-D7: Async reset while active");
    load_param(4'd0, 32'd777);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-D7 active before reset", v_drive, 14'd777);
    // Assert reset asynchronously (not on clock edge)
    #3; rst_n <= 0;
    #2;
    check_zero("TC-D7 v_drive=0 after async reset", v_drive);
    rst_n <= 1;
    @(negedge clk); active <= 0;

    // ----------------------------------------------------------------
    // TC-D8: Param write while active (live update check)
    // ----------------------------------------------------------------
    $display("TC-D8: Param write while active");
    @(negedge clk); do_reset(2);
    load_param(4'd0, 32'd100);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-D8 initial", v_drive, 14'd100);
    // Write new value while active
    @(negedge clk);
    en           <= 1;
    i_param_addr <= 4'd0;
    i_param_data <= 32'd200;
    @(negedge clk);
    en <= 0;
    @(posedge clk); #1;
    check("TC-D8 updated live", v_drive, 14'd200);
    @(negedge clk); active <= 0;

    // ---- Final report ----
    $display("=== tb_delay: %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("PASS: delay block");
    else
        $fatal(1, "FAIL: delay block has %0d failures", fail_count);

    $finish;
end

// ---- Timeout watchdog ----
initial begin
    #100000;
    $fatal(1, "TIMEOUT: tb_delay exceeded 100000 time units");
end

endmodule
`default_nettype wire
