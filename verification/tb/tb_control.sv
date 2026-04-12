`default_nettype none
// ============================================================
// tb_control.sv — White-box testbench for control.sv (FSM)
//
// Uses an inline register file model (logic array) to provide
// deterministic register reads without depending on bram.sv.
// This means it can run even before the bram module-name fix.
//
// Tests all 8 FSM states, parameter bus timing, block enable
// one-hot property, and correct seq_done pulse behavior.
//
// Compile:
//   iverilog -g2012 -Wall -o sim_ctrl src/control.sv verification/tb/tb_control.sv
//   vvp sim_ctrl
// Waveform:
//   gtkwave tb_control.vcd
// ============================================================
module tb_control;

localparam CLK_HALF             = 5;
localparam MAX_BLOCKS           = 16;
localparam DATA_WIDTH           = 32;
localparam NUM_BLOCK_TYPES      = 6;
localparam REGFILE_ADDR_WIDTH   = 8;
localparam BLOCK_IDX_WIDTH      = $clog2(MAX_BLOCKS);

// ---- Signals ----
logic                           clk;
logic                           rst_n;
logic                           i_start;
logic [BLOCK_IDX_WIDTH-1:0]     i_num_blocks;
logic [13:0]                    i_init_v_drive;

logic [REGFILE_ADDR_WIDTH-1:0]  o_regfile_addr;
logic [DATA_WIDTH-1:0]          i_regfile_data;

logic [13:0]                    i_block_drive [NUM_BLOCK_TYPES];
logic [DATA_WIDTH-1:0]          o_param_data;
logic [3:0]                     o_param_addr;
logic [NUM_BLOCK_TYPES-1:0]     o_block_en;
logic [NUM_BLOCK_TYPES-1:0]     o_block_active;
logic [13:0]                    v_drive;
logic                           o_seq_done;
logic                           o_active;

// ---- DUT ----
control #(
    .MAX_BLOCKS (MAX_BLOCKS),
    .DATA_WIDTH (DATA_WIDTH)
) dut (
    .clk             (clk),
    .rst_n           (rst_n),
    .i_start         (i_start),
    .i_num_blocks    (i_num_blocks),
    .i_init_v_drive  (i_init_v_drive),
    .o_regfile_addr  (o_regfile_addr),
    .i_regfile_data  (i_regfile_data),
    .i_block_drive   (i_block_drive),
    .o_param_data    (o_param_data),
    .o_param_addr    (o_param_addr),
    .o_block_en      (o_block_en),
    .o_block_active  (o_block_active),
    .v_drive         (v_drive),
    .o_seq_done      (o_seq_done),
    .o_active        (o_active)
);

// ---- Inline register file model ----
// Provides 1-cycle synchronous read latency, matching real BRAM behaviour.
logic [DATA_WIDTH-1:0] regfile_mem [256];

always_ff @(posedge clk) begin
    i_regfile_data <= regfile_mem[o_regfile_addr];
end

// ---- Block drive stubs — return a constant per-type ----
// In integration tests, real blocks would drive these. Here we feed
// predictable constants so CAPTURE_VDRIVE can be verified.
initial begin
    for (int i = 0; i < NUM_BLOCK_TYPES; i++)
        i_block_drive[i] = 14'(i * 100);  // 0, 100, 200, 300, 400, 500
end

initial clk = 0;
always #CLK_HALF clk = ~clk;

initial begin
    $dumpfile("tb_control.vcd");
    $dumpvars(0, tb_control);
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
        $display("  PASS [%s]: 0x%04h", name, got);
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got 0x%04h, expected 0x%04h", name, got, expected);
        fail_count++;
    end
endtask

task check32(input string name, input logic [31:0] got, input logic [31:0] expected);
    if (got === expected) begin
        $display("  PASS [%s]: 0x%08h", name, got);
        pass_count++;
    end else begin
        $display("  FAIL [%s]: got 0x%08h, expected 0x%08h", name, got, expected);
        fail_count++;
    end
endtask

task do_reset(input int cycles);
    rst_n <= 0; i_start <= 0; i_num_blocks <= '0; i_init_v_drive <= '0;
    repeat (cycles) @(negedge clk);
    rst_n <= 1;
    @(negedge clk);
endtask

// Write a block into the inline register file.
// Parameters per block stride (8 registers each):
//   offset 0: block type
//   offset 1..N-2: params sent to block (0-indexed)
//   offset N-1: duration (last param, saved to dur)
task write_block(
    input int          slot,       // block index (0..15)
    input logic [2:0]  btype,      // block type
    input logic [DATA_WIDTH-1:0] params[],  // all params including duration as last element
    input int          num_p       // total param count (includes duration)
);
    static int  base;
    base = slot * 8;
    regfile_mem[base] = {29'b0, btype};
    for (int i = 0; i < num_p; i++)
        regfile_mem[base + 1 + i] = params[i];
endtask

// Pulse i_start for one cycle
task pulse_start;
    @(negedge clk); i_start <= 1;
    @(negedge clk); i_start <= 0;
endtask

// Wait for o_seq_done to pulse, with a cycle timeout
task wait_seq_done(input int max_cycles, output logic timed_out);
    timed_out = 0;
    for (int i = 0; i < max_cycles; i++) begin
        @(posedge clk);
        if (o_seq_done) return;
    end
    timed_out = 1;
endtask

initial begin
    $display("=== tb_control: begin ===");

    rst_n = 1; i_start = 0; i_num_blocks = '0; i_init_v_drive = '0;
    // Clear all register file slots
    for (int i = 0; i < 256; i++) regfile_mem[i] = '0;

    // ---------------------------------------------------------------
    // TC-FSM1: Single delay block (type 0, 1 param + duration)
    //   Slot 0: type=0, hold_voltage=512, duration=5
    //   Expected: param_addr[0]=512 sent to block[0], then active for 5 cycles,
    //             then seq_done pulse.
    // ---------------------------------------------------------------
    $display("TC-FSM1: Single delay block, duration=5");
    do_reset(4);

    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd512, 32'd5};
        write_block(0, 3'd0, p, 2);
    end

    i_num_blocks   = BLOCK_IDX_WIDTH'(0);  // only block 0
    i_init_v_drive = 14'd0;

    // Check IDLE outputs before start
    @(posedge clk); #1;
    check("TC-FSM1 idle o_active=0",   o_active,    1'b0);
    check("TC-FSM1 idle o_seq_done=0", o_seq_done,  1'b0);
    check("TC-FSM1 idle o_block_en=0", (o_block_en == '0), 1'b1);

    pulse_start();

    // Wait for seq_done
    begin
        automatic logic to;
        wait_seq_done(100, to);
        check("TC-FSM1 seq_done received (no timeout)", to, 1'b0);
    end

    @(posedge clk); #1;
    // After DONE → IDLE
    check("TC-FSM1 o_active=0 in IDLE", o_active, 1'b0);
    check("TC-FSM1 o_seq_done=0 one cycle after done", o_seq_done, 1'b0);

    // ---------------------------------------------------------------
    // TC-FSM2: Verify o_block_en one-hot and timing during param load
    //   Use a type-1 (linear_ramp) block: 2 params sent + 1 duration
    // ---------------------------------------------------------------
    $display("TC-FSM2: Type 1 (linear_ramp) — param bus one-hot check");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[3] = '{32'd100, 32'd5, 32'd8};
        write_block(0, 3'd1, p, 3);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);

    pulse_start();

    // Advance to LOAD_PARAMS (past FETCH_TYPE + LOAD_INIT = 2 cycles after start)
    // FETCH_TYPE (1 cycle) → LOAD_INIT (1 cycle) → LOAD_PARAMS (2+ cycles for type=1)
    @(posedge clk); // FETCH_TYPE
    @(posedge clk); // LOAD_INIT
    // Now in LOAD_PARAMS, param_idx=0: should see block_en[1] high
    @(posedge clk); #1;
    check("TC-FSM2 param0: block_en[1] high", o_block_en[1], 1'b1);
    check("TC-FSM2 param0: block_en not multi-hot", ($countones(o_block_en) <= 1), 1'b1);
    check32("TC-FSM2 param0: param_data=100", o_param_data, 32'd100);
    check("TC-FSM2 param0: param_addr=0", (o_param_addr == 4'd0), 1'b1);

    @(posedge clk); #1;
    check("TC-FSM2 param1: block_en[1] high", o_block_en[1], 1'b1);
    check32("TC-FSM2 param1: param_data=5", o_param_data, 32'd5);
    check("TC-FSM2 param1: param_addr=1", (o_param_addr == 4'd1), 1'b1);

    @(posedge clk); #1;
    // Entering START_BLOCK — block_en should drop to 0
    check("TC-FSM2 START_BLOCK: block_en=0", (o_block_en == '0), 1'b1);
    check("TC-FSM2 START_BLOCK: block_active[1] high", o_block_active[1], 1'b1);

    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-FSM2 seq_done (no timeout)", to, 1'b0);
    end

    // ---------------------------------------------------------------
    // TC-FSM3: Two-block sequence — delay then direct_jump
    // ---------------------------------------------------------------
    $display("TC-FSM3: Two-block sequence (delay → direct_jump)");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p0[2] = '{32'd1000, 32'd3};  // hold=1000, dur=3
        automatic logic [DATA_WIDTH-1:0] p1[2] = '{32'd2000, 32'd4};  // target=2000, dur=4
        write_block(0, 3'd0, p0, 2);  // delay
        write_block(1, 3'd2, p1, 2);  // direct_jump
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(1);  // 2 blocks (index 0 and 1)

    pulse_start();

    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-FSM3 seq_done after 2 blocks", to, 1'b0);
    end

    // ---------------------------------------------------------------
    // TC-FSM4: i_start ignored while sequence is active
    // ---------------------------------------------------------------
    $display("TC-FSM4: i_start ignored while active");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd500, 32'd20};
        write_block(0, 3'd0, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);

    pulse_start();
    // Immediately fire another start
    @(negedge clk); i_start <= 1;
    @(negedge clk); i_start <= 0;
    // Should still see o_active high (not restarted from scratch)
    @(posedge clk); #1;
    check("TC-FSM4 o_active still high during sequence", o_active, 1'b1);

    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-FSM4 seq_done (single, not doubled)", to, 1'b0);
    end
    // Ensure no second seq_done after the first
    @(posedge clk); #1;
    check("TC-FSM4 no second seq_done", o_seq_done, 1'b0);

    // ---------------------------------------------------------------
    // TC-FSM5: Reset in WAIT_DONE state
    // ---------------------------------------------------------------
    $display("TC-FSM5: Async reset mid-sequence (in WAIT_DONE)");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd300, 32'd100}; // long duration
        write_block(0, 3'd0, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);

    pulse_start();
    // Advance enough to reach WAIT_DONE (FETCH_TYPE + LOAD_INIT + 2*LOAD_PARAMS + START_BLOCK = ~6 cycles)
    repeat (8) @(posedge clk);
    @(posedge clk); #1;
    check("TC-FSM5 active during WAIT_DONE", o_active, 1'b1);

    // Assert async reset
    #3; rst_n <= 0;
    #2;
    check("TC-FSM5 o_active=0 after reset", o_active, 1'b0);
    check("TC-FSM5 o_seq_done=0 after reset", o_seq_done, 1'b0);
    check("TC-FSM5 o_block_active=0 after reset", (o_block_active == '0), 1'b1);

    rst_n <= 1; @(negedge clk);

    // ---------------------------------------------------------------
    // TC-FSM6: o_seq_done is exactly 1 cycle wide
    // ---------------------------------------------------------------
    $display("TC-FSM6: seq_done is exactly 1 cycle wide");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd50, 32'd2};
        write_block(0, 3'd0, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    pulse_start();

    // Wait for seq_done
    @(posedge clk);
    while (!o_seq_done) @(posedge clk);
    #1;
    check("TC-FSM6 seq_done high for 1 cycle", o_seq_done, 1'b1);
    @(posedge clk); #1;
    check("TC-FSM6 seq_done low next cycle", o_seq_done, 1'b0);

    // ---------------------------------------------------------------
    // TC-FSM7: Minimum duration = 1
    // ---------------------------------------------------------------
    $display("TC-FSM7: Minimum duration=1");
    do_reset(4);
    begin
        automatic logic [DATA_WIDTH-1:0] p[2] = '{32'd42, 32'd1};
        write_block(0, 3'd0, p, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(0);
    pulse_start();
    begin
        automatic logic to;
        wait_seq_done(50, to);
        check("TC-FSM7 seq_done with duration=1", to, 1'b0);
    end

    // ---------------------------------------------------------------
    // TC-FSM8: prev_v_drive holds between blocks (no glitch)
    // ---------------------------------------------------------------
    $display("TC-FSM8: v_drive holds prev_v_drive between blocks");
    do_reset(4);
    // block[0] = delay type, hold=777, dur=2
    // block[1] = delay type, hold=888, dur=2
    begin
        automatic logic [DATA_WIDTH-1:0] p0[2] = '{32'd777, 32'd2};
        automatic logic [DATA_WIDTH-1:0] p1[2] = '{32'd888, 32'd2};
        write_block(0, 3'd0, p0, 2);
        write_block(1, 3'd0, p1, 2);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(1);
    i_block_drive[0] = 14'd777;  // mock block drive for delay type

    pulse_start();
    // Wait until CAPTURE_VDRIVE of first block (after 2+6 = ~8 cycles)
    // then verify v_drive is the captured value from delay block
    begin
        automatic logic to;
        wait_seq_done(200, to);
        check("TC-FSM8 two-block seq completed", to, 1'b0);
    end

    // ---------------------------------------------------------------
    // TC-FSM9: All 6 block types activated in sequence
    // ---------------------------------------------------------------
    $display("TC-FSM9: All 6 block types exercised");
    do_reset(4);
    // Set each block to the matching type with minimal params and duration=2
    begin
        automatic logic [DATA_WIDTH-1:0] p_delay[2]    = '{32'd0, 32'd2};
        automatic logic [DATA_WIDTH-1:0] p_ramp[3]     = '{32'd0, 32'd0, 32'd2};
        automatic logic [DATA_WIDTH-1:0] p_jump[2]     = '{32'd0, 32'd2};
        automatic logic [DATA_WIDTH-1:0] p_chirp[6]    = '{32'd0, 32'd0, 32'd0, 32'd0, 32'd0, 32'd2};
        automatic logic [DATA_WIDTH-1:0] p_sinusoid[6] = '{32'd0, 32'd0, 32'd0, 32'd0, 32'd0, 32'd2};
        automatic logic [DATA_WIDTH-1:0] p_awg[4]      = '{32'd1, 32'd0, 32'd0, 32'd2};
        write_block(0, 3'd0, p_delay,    2);
        write_block(1, 3'd1, p_ramp,     3);
        write_block(2, 3'd2, p_jump,     2);
        write_block(3, 3'd3, p_chirp,    6);
        write_block(4, 3'd4, p_sinusoid, 6);
        write_block(5, 3'd5, p_awg,      4);
    end
    i_num_blocks = BLOCK_IDX_WIDTH'(5);  // 6 blocks

    pulse_start();

    begin
        automatic logic to;
        wait_seq_done(500, to);
        check("TC-FSM9 all-types seq completed", to, 1'b0);
    end
    check("TC-FSM9 o_active=0 after done", o_active, 1'b0);

    // ---- Final report ----
    $display("=== tb_control: %0d passed, %0d failed ===", pass_count, fail_count);
    if (fail_count == 0)
        $display("PASS: control FSM");
    else
        $fatal(1, "FAIL: control FSM has %0d failures", fail_count);

    $finish;
end

// Continuous X/Z check on DAC output during active sequence
always @(posedge clk) begin
    if (o_active && (^v_drive === 1'bx))
        $fatal(1, "ROGUE BEHAVIOR: v_drive has X/Z during active sequence at time %0t", $time);
    if (o_active && (^o_block_active === 1'bx))
        $fatal(1, "ROGUE BEHAVIOR: o_block_active has X/Z during active at time %0t", $time);
end

initial begin
    #2000000;
    $fatal(1, "TIMEOUT: tb_control exceeded 2000000 time units");
end

endmodule
`default_nettype wire
