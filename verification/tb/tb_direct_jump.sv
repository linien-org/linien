`default_nettype none
// ============================================================
// tb_direct_jump.sv — Testbench for direct_jump.sv (Block Type 2)
//
// Compile:
//   iverilog -g2012 -Wall -o sim_dj src/direct_jump.sv verification/tb/tb_direct_jump.sv
//   vvp sim_dj
// Waveform:
//   gtkwave tb_direct_jump.vcd
// ============================================================
module tb_direct_jump;

localparam CLK_HALF  = 5;
localparam DATA_WIDTH = 32;

logic                  clk;
logic                  rst_n;
logic                  en;
logic [DATA_WIDTH-1:0] i_param_data;
logic [3:0]            i_param_addr;
logic                  active;
logic [13:0]           v_drive;

direct_jump #(
    .DATA_WIDTH (DATA_WIDTH)
) dut (
    .clk          (clk),
    .rst_n        (rst_n),
    .en           (en),
    .active       (active),
    .i_param_data (i_param_data),
    .i_param_addr (i_param_addr),
    .v_drive      (v_drive)
);

initial clk = 0;
always #CLK_HALF clk = ~clk;

initial begin
    $dumpfile("tb_direct_jump.vcd");
    $dumpvars(0, tb_direct_jump);
end

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

task do_reset(input int cycles);
    rst_n <= 0; en <= 0; active <= 0; i_param_data <= '0; i_param_addr <= '0;
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

initial begin
    $display("=== tb_direct_jump: begin ===");

    rst_n = 1; en = 0; active = 0; i_param_data = '0; i_param_addr = '0;

    // TC-DJ1: Reset
    $display("TC-DJ1: Reset assertion");
    do_reset(4);
    @(posedge clk); #1;
    check("TC-DJ1 v_drive after reset", v_drive, 14'h0);

    // TC-DJ2: Nominal — jump to 1000
    $display("TC-DJ2: Jump to 1000");
    load_param(4'd0, 32'd1000);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-DJ2 v_drive=1000", v_drive, 14'd1000);

    // TC-DJ3: Deassert active
    $display("TC-DJ3: Deassert active");
    @(negedge clk); active <= 0;
    @(posedge clk); #1;
    check("TC-DJ3 v_drive=0 inactive", v_drive, 14'h0);

    // TC-DJ4: Jump to 0
    $display("TC-DJ4: Jump to 0");
    load_param(4'd0, 32'd0);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-DJ4 v_drive=0", v_drive, 14'h0);
    @(negedge clk); active <= 0;

    // TC-DJ5: Max 14-bit value (0x3FFF)
    $display("TC-DJ5: Max value");
    load_param(4'd0, 32'h0000_3FFF);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-DJ5 v_drive=max", v_drive, 14'h3FFF);
    @(negedge clk); active <= 0;

    // TC-DJ6: High bits of param ignored (only [13:0] used)
    $display("TC-DJ6: Upper bits of param data ignored");
    load_param(4'd0, 32'hDEAD_0123);  // [13:0] = 0x0123 = 291
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-DJ6 only [13:0] captured", v_drive, 14'h0123);
    @(negedge clk); active <= 0;

    // TC-DJ7: Invalid param addr — v_target unchanged
    $display("TC-DJ7: Invalid param address ignored");
    load_param(4'd0, 32'd500);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-DJ7 pre-invalid", v_drive, 14'd500);
    load_param(4'd1, 32'd999);  // invalid addr
    @(posedge clk); #1;
    check("TC-DJ7 unchanged after invalid addr", v_drive, 14'd500);
    @(negedge clk); active <= 0;

    // TC-DJ8: Async reset mid-operation
    $display("TC-DJ8: Async reset mid-operation");
    load_param(4'd0, 32'd777);
    @(negedge clk); active <= 1;
    @(posedge clk); #1;
    check("TC-DJ8 before reset", v_drive, 14'd777);
    #3; rst_n <= 0;
    #2;
    check("TC-DJ8 v_drive=0 after async reset", v_drive, 14'h0);
    rst_n <= 1;
    @(negedge clk); active <= 0;

    $display("=== tb_direct_jump: %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("PASS: direct_jump block");
    else
        $fatal(1, "FAIL: direct_jump block has %0d failures", fail_count);

    $finish;
end

initial begin
    #100000;
    $fatal(1, "TIMEOUT: tb_direct_jump exceeded 100000 time units");
end

endmodule
`default_nettype wire
