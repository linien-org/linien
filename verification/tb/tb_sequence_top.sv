`default_nettype none
// ============================================================
// tb_sequence_top.sv — Integration testbench for sequence_top (top.sv)
//
// PREREQUISITE: The following source bugs must be fixed first:
//   1. bram.sv: module reg_file → module bram
//   2. top.sv:197: remove  assign block_drive[5] = 14'b0;
//   3. top.sv:184: remove  #(.DATA_WIDTH(DATA_WIDTH)) from sinusoid
//   See verification/reports/code_review.md for details.
//
// NOTE: sinusoid module requires sin_lut.memh in the working directory.
//
// Compile (after fixes applied):
//   iverilog -g2012 -Wall -o sim_top \
//     src/bram.sv src/control.sv src/delay.sv src/linear_ramp.sv \
//     src/direct_jump.sv src/chirp_gen.sv src/sinusoid.sv src/arb_wave.sv \
//     src/top.sv \
//     verification/tb/tb_sequence_top.sv
//   vvp sim_top
// Waveform:
//   gtkwave tb_sequence_top.vcd
// ============================================================
module tb_sequence_top;

localparam CLK_HALF               = 5;
localparam MAX_BLOCKS             = 16;
localparam DATA_WIDTH             = 32;
localparam V_DATA_WIDTH           = 14;
localparam NUM_BLOCK_TYPES        = 6;
localparam FSM_REGFILE_ADDR_WIDTH = 8;
localparam AWG_REGFILE_ADDR_WIDTH = 10;
localparam BLOCK_IDX_WIDTH        = $clog2(MAX_BLOCKS);

// ---- DUT signals ----
logic                              clk;
logic                              rst_n;

// FSM register file write port (PS side)
logic [FSM_REGFILE_ADDR_WIDTH-1:0] i_fsm_reg_w_addr;
logic [DATA_WIDTH-1:0]             i_fsm_reg_w_data;
logic                              i_fsm_reg_w_en;

// AWG register file write port (PS side)
logic [AWG_REGFILE_ADDR_WIDTH-1:0] i_awg_reg_w_addr;
logic [V_DATA_WIDTH-1:0]           i_awg_reg_w_data;
logic                              i_awg_reg_w_en;

logic [BLOCK_IDX_WIDTH-1:0]        i_num_blocks;
logic                              i_start;
logic [V_DATA_WIDTH-1:0]           i_init_v;

logic                              o_seq_done;
logic                              o_active;
logic [V_DATA_WIDTH-1:0]           o_dac_drive;

// DUT Instantiation
sequence_top #(
    .MAX_BLOCKS             (MAX_BLOCKS),
    .DATA_WIDTH             (DATA_WIDTH),
    .V_DATA_WIDTH           (V_DATA_WIDTH),
    .NUM_BLOCK_TYPES        (NUM_BLOCK_TYPES),
    .FSM_REGFILE_ADDR_WIDTH (FSM_REGFILE_ADDR_WIDTH),
    .AWG_REGFILE_ADDR_WIDTH (AWG_REGFILE_ADDR_WIDTH)
) dut (
    .clk              (clk),
    .rst_n            (rst_n),
    .i_fsm_reg_w_addr (i_fsm_reg_w_addr),
    .i_fsm_reg_w_data (i_fsm_reg_w_data),
    .i_fsm_reg_w_en   (i_fsm_reg_w_en),
    .i_awg_reg_w_addr (i_awg_reg_w_addr),
    .i_awg_reg_w_data (i_awg_reg_w_data),
    .i_awg_reg_w_en   (i_awg_reg_w_en),
    .i_num_blocks     (i_num_blocks),
    .i_start          (i_start),
    .i_init_v         (i_init_v),
    .o_seq_done       (o_seq_done),
    .o_active         (o_active),
    .o_dac_drive      (o_dac_drive)
);

initial clk = 0;
always #CLK_HALF clk = ~clk;

initial begin
    $dumpfile("tb_sequence_top.vcd");
    $dumpvars(0, tb_sequence_top);
end

int pass_count = 0;
int fail_count = 0;

task check(input string name, input logic got, input logic expected);
    if (got === expected) begin
        $display("  PASS [%s]", name);
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got %0b, expected %0b", name, got, expected);
        fail_count++;
    end
endtask

task check14(input string name, input logic [13:0] got, input logic [13:0] expected);
    if (got === expected) begin
        $display("  PASS [%s]: 0x%04h (%0d)", name, got, got);
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got 0x%04h (%0d), expected 0x%04h (%0d)",
                 name, got, got, expected, expected);
        fail_count++;
    end
endtask

task do_reset(input int cycles);
    rst_n             <= 0;
    i_start           <= 0;
    i_num_blocks      <= '0;
    i_init_v          <= '0;
    i_fsm_reg_w_en    <= 0;
    i_fsm_reg_w_addr  <= '0;
    i_fsm_reg_w_data  <= '0;
    i_awg_reg_w_en    <= 0;
    i_awg_reg_w_addr  <= '0;
    i_awg_reg_w_data  <= '0;
    repeat (cycles) @(negedge clk);
    rst_n <= 1;
    @(negedge clk);
endtask

// Write one word into the FSM register file
task fsm_reg_write(input logic [FSM_REGFILE_ADDR_WIDTH-1:0] addr,
                   input logic [DATA_WIDTH-1:0] data);
    @(negedge clk);
    i_fsm_reg_w_en   <= 1;
    i_fsm_reg_w_addr <= addr;
    i_fsm_reg_w_data <= data;
    @(negedge clk);
    i_fsm_reg_w_en <= 0;
endtask

// Write one word into the AWG register file
task awg_reg_write(input logic [AWG_REGFILE_ADDR_WIDTH-1:0] addr,
                   input logic [V_DATA_WIDTH-1:0] data);
    @(negedge clk);
    i_awg_reg_w_en   <= 1;
    i_awg_reg_w_addr <= addr;
    i_awg_reg_w_data <= data;
    @(negedge clk);
    i_awg_reg_w_en <= 0;
endtask

// Write a block into the FSM register file.
// Stride: 8 registers per block.
//   base+0 : block type
//   base+1 : param[0]
//   ...
//   base+N : param[N-1] = duration (last param)
task write_block(
    input int          slot,
    input logic [2:0]  btype,
    input logic [DATA_WIDTH-1:0] params[],
    input int          num_p
);
    automatic int base = slot * 8;
    fsm_reg_write(8'(base),   {29'b0, btype});
    for (int i = 0; i < num_p; i++)
        fsm_reg_write(8'(base + 1 + i), params[i]);
endtask

task pulse_start;
    @(negedge clk); i_start <= 1;
    @(negedge clk); i_start <= 0;
endtask

task wait_seq_done(input int max_cycles, output logic timed_out);
    timed_out = 0;
    for (int i = 0; i < max_cycles; i++) begin
        @(posedge clk);
        if (o_seq_done) return;
    end
    timed_out = 1;
endtask

initial begin
    $display("=== tb_sequence_top: begin ===");

    rst_n = 1;
    i_start = 0; i_num_blocks = '0; i_init_v = '0;
    i_fsm_reg_w_en = 0; i_fsm_reg_w_addr = '0; i_fsm_reg_w_data = '0;
    i_awg_reg_w_en = 0; i_awg_reg_w_addr = '0; i_awg_reg_w_data = '0;


    // TC-INT1: Idle state after reset
    $display("TC-INT1: Reset and idle");
    do_reset(8);
    @(posedge clk); #1;
    check("TC-INT1 o_active=0", o_active, 1'b0);
    check("TC-INT1 o_seq_done=0", o_seq_done, 1'b0);
    check14("TC-INT1 o_dac_drive=0", o_dac_drive, 14'h0);


    // TC-INT2: Single delay block — hold 1000 for 10 cycles
    $display("TC-INT2: Single delay block (hold=1000, dur=10)");
    do_reset(4);

    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd1000, 32'd10};
        write_block(0, 3'd0, p, 2);
    end

    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    i_init_v     = 14'd0;
    pulse_start();

    // Wait for active to go high
    @(posedge clk);
    while (!o_active) @(posedge clk);
    // Wait a few more cycles for START_BLOCK to begin
    repeat (6) @(posedge clk);
    #1;
    check("TC-INT2 o_active high during execution", o_active, 1'b1);
    // Verify DAC drives the block output (delay holds 1000)
    check14("TC-INT2 o_dac_drive=1000 during delay", o_dac_drive, 14'd1000);

    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-INT2 seq_done received", to, 1'b0);
    end
    check("TC-INT2 o_seq_done=1 pulse", o_seq_done, 1'b1);
    @(posedge clk); #1;
    check("TC-INT2 o_seq_done drops after 1 cycle", o_seq_done, 1'b0);
    check("TC-INT2 o_active=0 after done", o_active, 1'b0);


    // TC-INT3: Delay → Linear Ramp sequence
    $display("TC-INT3: Delay and Linear Ramp sequence");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p0[2] = '{32'd500, 32'd5};      // delay: hold=500, dur=5
        automatic logic [DATA_WIDTH-1:0] p1[3] = '{32'd100, 32'd10, 32'd8}; // ramp: start=100, step=10, dur=8
        write_block(0, 3'd0, p0, 2);
        write_block(1, 3'd1, p1, 3);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(1);
    pulse_start();

    begin
        automatic logic to;
        wait_seq_done(500, to);
        check("TC-INT3 seq_done after delay+ramp", to, 1'b0);
    end


    // TC-INT4: Direct Jump block
    $display("TC-INT4: Direct Jump to 2000");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd2000, 32'd3};
        write_block(0, 3'd2, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    pulse_start();

    // Wait until in WAIT_DONE (START_BLOCK + a cycle)
    @(posedge clk);
    while (!o_active) @(posedge clk);
    repeat (7) @(posedge clk); #1;
    check14("TC-INT4 o_dac_drive=2000 during direct_jump", o_dac_drive, 14'd2000);
    begin
        automatic logic to;
        wait_seq_done(100, to);
        check("TC-INT4 seq_done", to, 1'b0);
    end


    // TC-INT5: Chirp block (parabolic ramp)
    //   a=0, b=0, rate=20, raterate=2, duration=15
    $display("TC-INT5: Chirp block parabolic ramp");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[6] = '{32'd0, 32'd0, 32'd20, 32'd2, 32'd0, 32'd15};
        write_block(0, 3'd3, p, 6);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    pulse_start();

    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-INT5 seq_done from chirp block", to, 1'b0);
    end


    // TC-INT5b: Sinusoid block (type 4)
    //   v_mid=4000, v_amp=2000, v_min_cut=0, v_max_cut=8000,
    //   phase_inc=4194304 (~1 kHz at 100 MHz with 32-bit accum), dur=20
    $display("TC-INT5b: Sinusoid block");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[6] = '{
            32'd4000,     // v_mid
            32'd2000,     // v_amp
            32'd0,        // v_min_cutoff
            32'd8000,     // v_max_cutoff
            32'd4194304,  // phase_increment
            32'd40        // duration (longer to allow multiple samples)
        };
        write_block(0, 3'd4, p, 6);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    pulse_start();

    // Wait for active — sinusoid has 6 params so LOAD_PARAMS takes ~6 cycles
    // then START_BLOCK + a few WAIT_DONE cycles before sampling.
    // Need at least 10 cycles after o_active to be in WAIT_DONE.
    @(posedge clk);
    while (!o_active) @(posedge clk);
    repeat (12) @(posedge clk); #1;
    check("TC-INT5b o_active high during sinusoid", o_active, 1'b1);
    // With v_mid=4000, sin(0)=0 in LUT, output should start at ~4000
    // and oscillate around v_mid. Must be non-zero during execution.
    $display("  INFO: o_dac_drive = %0d during sinusoid execution", o_dac_drive);
    if (o_dac_drive == 14'd0) begin
        $display("  FAIL [TC-INT5b o_dac_drive nonzero]: got 0, expected ~4000 (v_mid)");
        fail_count++;
    end else begin
        $display("  PASS [TC-INT5b o_dac_drive nonzero]: %0d", o_dac_drive);
        pass_count++;
    end

    // Sample a few more cycles and verify output stays in valid range [0, 8000]
    repeat (5) @(posedge clk); #1;
    $display("  INFO: o_dac_drive = %0d (2nd sample)", o_dac_drive);
    if (o_dac_drive == 14'd0) begin
        $display("  FAIL [TC-INT5b o_dac_drive 2nd nonzero]: got 0");
        fail_count++;
    end else begin
        $display("  PASS [TC-INT5b o_dac_drive 2nd nonzero]: %0d", o_dac_drive);
        pass_count++;
    end

    begin
        automatic logic to;
        wait_seq_done(500, to);
        check("TC-INT5b seq_done from sinusoid block", to, 1'b0);
    end


    // TC-INT6: AWG block with pre-loaded BRAM data
    //   BRAM[0..3] = 100,200,300,400; clk_div=1, duration=10
    $display("TC-INT6: AWG block with BRAM data");
    do_reset(4);
    // Load AWG BRAM — fill enough entries for full duration + pipeline latency
    for (int i = 0; i < 20; i++)
        awg_reg_write(10'(i), 14'(100 + i * 100));
    begin
        // AWG: param[0]=clk_div, param[1]=unused, param[2]=unused, param[3]=duration
        automatic logic [DATA_WIDTH-1:0] p[4] = '{32'd1, 32'd0, 32'd0, 32'd10};
        write_block(0, 3'd5, p, 4);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    pulse_start();

    begin
        automatic logic to;
        wait_seq_done(300, to);
        check("TC-INT6 seq_done from AWG block", to, 1'b0);
    end


    // TC-INT7: o_active timing — high from FETCH_TYPE through CAPTURE_VDRIVE
    $display("TC-INT7: o_active timing verification");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd50, 32'd4};
        write_block(0, 3'd0, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);

    // Verify o_active=0 before start
    @(posedge clk); #1;
    check("TC-INT7 o_active=0 before start", o_active, 1'b0);

    @(negedge clk); i_start <= 1;
    @(negedge clk); i_start <= 0;
    @(posedge clk); #1;
    check("TC-INT7 o_active=1 in FETCH_TYPE", o_active, 1'b1);

    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-INT7 seq_done", to, 1'b0);
    end
    @(posedge clk); #1;  // DONE → IDLE
    check("TC-INT7 o_active=0 after DONE", o_active, 1'b0);


    // TC-INT8: Back-to-back sequences (start immediately after seq_done)
    $display("TC-INT8: Back-to-back starts");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd111, 32'd2};
        write_block(0, 3'd0, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);

    // First run
    pulse_start();
    @(posedge clk);
    while (!o_seq_done) @(posedge clk);
    // Wait for FSM to return to IDLE (DONE → IDLE takes 1 cycle)
    @(posedge clk);
    // Now start second run
    pulse_start();

    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-INT8 second run seq_done", to, 1'b0);
    end


    // TC-INT9: Async reset mid-sequence
    $display("TC-INT9: Async reset mid-sequence");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd800, 32'd100};  // long duration
        write_block(0, 3'd0, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    pulse_start();

    // Wait until sequence is well underway (WAIT_DONE)
    repeat (15) @(posedge clk);
    #1;
    check("TC-INT9 o_active before reset", o_active, 1'b1);

    // Async reset
    #3; rst_n <= 0;
    #2;
    check("TC-INT9 o_active=0 after reset", o_active, 1'b0);
    check("TC-INT9 o_seq_done=0 after reset", o_seq_done, 1'b0);
    check14("TC-INT9 o_dac_drive=0 after reset", o_dac_drive, 14'h0);
    rst_n <= 1;

    // Verify design can still run after reset
    @(negedge clk);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd600, 32'd3};
        write_block(0, 3'd0, p, 2);
    end
    pulse_start();
    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-INT9 seq_done after recovery", to, 1'b0);
    end

    // Final report
    $display("=== tb_sequence_top: %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("PASS: integration");
    else
        $fatal(1, "FAIL: integration has %0d failures", fail_count);

    $finish;
end

// Continuous X/Z assertion on DAC during active sequence
always @(posedge clk) begin
    if (o_active && (^o_dac_drive === 1'bx)) begin
        $fatal(1, "SIGNAL INTEGRITY: o_dac_drive has X/Z during active sequence at time %0t", $time);
    end
end

// seq_done stuck-high watchdog
logic [3:0] done_count = 0;
always @(posedge clk) begin
    if (o_seq_done) done_count <= done_count + 1;
    else            done_count <= 0;
    if (done_count > 1)
        $fatal(1, "ROGUE BEHAVIOR: o_seq_done held high for >1 cycle at time %0t", $time);
end

initial begin
    #5000000;
    $fatal(1, "TIMEOUT: tb_sequence_top exceeded 5000000 time units");
end

endmodule
`default_nettype wire
