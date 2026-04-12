`default_nettype none

module top #(
    parameter int MAX_BLOCKS = 16,
    parameter int DATA_WIDTH = 32,
    parameter int V_DATA_WIDTH = 14,
    parameter int NUM_BLOCK_TYPES = 6,
    parameter int FSM_REGFILE_ADDR_WIDTH = 8,
    parameter int AWG_REGFILE_ADDR_WIDTH = 10

    //auto-calculated parameters
  
) (
    input wire clk,
    input wire rst_n,

    //Signals from Regfile_Adapter for FSM (PS write to reg_file)
    input wire [FSM_REGFILE_ADDR_WIDTH-1:0] i_fsm_reg_w_addr,
    input wire [DATA_WIDTH-1:0] i_fsm_reg_w_data,
    input wire i_fsm_reg_w_en,

    //Signals from Regfile_Adapter for AWG (PS write to reg_file)
    input wire [AWG_REGFILE_ADDR_WIDTH-1:0] i_awg_reg_w_addr,
    input wire [V_DATA_WIDTH-1:0] i_awg_reg_w_data,
    input wire i_awg_reg_w_en,

    //Signal from Regfile_Adapter (config)
    input wire [BLOCK_IDX_WIDTH-1:0] i_num_blocks,   //last block index

    //signals from ttl handler
    input wire                     i_start,         //in ttl_handler, this is o_fsm_start
    input wire [13:0]              i_init_v,        //saved DAC voltage

    //Signals to ttl handler
    output logic                    o_seq_done,      //1 cycle pulse
    output logic                    o_active,        //high when sequence is active

    //DAC output (to linien)
    output logic [13:0]             o_dac_drive
);

//Internal Wires
  localparam int BLOCK_IDX_WIDTH = $clog2(MAX_BLOCKS);
    localparam int BLOCK_TYPE_IDX_WIDTH = $clog2(NUM_BLOCK_TYPES);
//reg file read port (control to reg_file)
logic [FSM_REGFILE_ADDR_WIDTH-1:0] reg_r_addr;
logic [DATA_WIDTH-1:0] reg_r_data;

//awg reg file read port (awg to reg_files)
logic [AWG_REGFILE_ADDR_WIDTH-1:0] awg_r_addr;
logic [V_DATA_WIDTH-1:0] awg_r_data;

//shared param bus (control to all blocks)
logic [DATA_WIDTH-1:0] param_bus_data;
logic [3:0] param_bus_addr;
logic [NUM_BLOCK_TYPES-1:0] block_en;
logic [NUM_BLOCK_TYPES-1:0] block_active;

//feedback from blocks to control
logic [V_DATA_WIDTH-1:0] block_drive [NUM_BLOCK_TYPES];


// input signals:  clk, rst_n
//                 ps write signals (i_ps_wr_addr, i_ps_wr_data, i_ps_wr_en)
// output signals: 
bram #(
        .ADDR_WIDTH (FSM_REGFILE_ADDR_WIDTH),
        .DATA_WIDTH (DATA_WIDTH)
    ) fsm_reg_file (
        .clk        (clk),

        // PS write port
        .i_wr_addr  (i_fsm_reg_w_addr),
        .i_wr_data  (i_fsm_reg_w_data),
        .i_wr_en    (i_fsm_reg_w_en),

        // Control read port
        .i_rd_addr  (reg_r_addr),
        .o_rd_data  (reg_r_data)
    );

bram #(
      .ADDR_WIDTH(AWG_REGFILE_ADDR_WIDTH),
      .DATA_WIDTH(V_DATA_WIDTH)
  ) BRAM (
      .clk(clk),

      // PS write port
      .i_wr_addr(i_awg_reg_w_addr),
      .i_wr_data(i_awg_reg_w_data),
      .i_wr_en(i_awg_reg_w_en),

      // Control read port
      .i_rd_addr(awg_r_addr),
      .o_rd_data(awg_r_data)
  );

control #(
    .MAX_BLOCKS (MAX_BLOCKS),
    .DATA_WIDTH (DATA_WIDTH)
) u_control (
    .clk            (clk),
    .rst_n          (rst_n),

    // Top-level control
    .i_start        (i_start),
    .i_num_blocks   (i_num_blocks),
    .i_init_v_drive (i_init_v),

    // Register file read port
    .o_regfile_addr (reg_r_addr),
    .i_regfile_data (reg_r_data),

    // Function block drive (no more i_block_done!)
    .i_block_drive  (block_drive),

    // Shared parameter bus
    .o_param_data   (param_bus_data),
    .o_param_addr   (param_bus_addr),

    // Per-block control
    .o_block_en     (block_en),
    .o_block_active (block_active),

    // DAC output
    .v_drive        (o_dac_drive),

    // Status
    .o_seq_done     (o_seq_done),
    .o_active       (o_active)
);

// Delay Block (type 0)
delay #(
    .DATA_WIDTH (DATA_WIDTH)
) u_delay (
    .clk          (clk),
    .rst_n        (rst_n),
    .en           (block_en[0]),
    .i_param_data (param_bus_data),
    .i_param_addr (param_bus_addr),
    .active       (block_active[0]),
    .v_drive      (block_drive[0])
);

// Linear Ramp Block (type 1)
linear_ramp #(
    .DATA_WIDTH (DATA_WIDTH)
) u_linear_ramp (
    .clk          (clk),
    .rst_n        (rst_n),
    .en           (block_en[1]),
    .i_param_data (param_bus_data),
    .i_param_addr (param_bus_addr),
    .i_active     (block_active[1]),
    .v_drive      (block_drive[1])
);

// Direct Jump Block (type 2)
direct_jump #(
    .DATA_WIDTH (DATA_WIDTH)
) u_direct_jump (
    .clk          (clk),
    .rst_n        (rst_n),
    .en           (block_en[2]),
    .i_param_data (param_bus_data),
    .i_param_addr (param_bus_addr),
    .active       (block_active[2]),
    .v_drive      (block_drive[2])
);

// Chirp Block (type 3)
chirp_gen u_chirp_gen (
    .clk          (clk),
    .rst_n        (rst_n),
    .en           (block_en[3]),
    .i_param_data (param_bus_data),
    .i_param_addr (param_bus_addr),
    .active       (block_active[3]),
    .voltage      (block_drive[3])
);

//Sinusoidal Block (type 4)
sinusoid #(
    .DATA_WIDTH (DATA_WIDTH)
) u_sinusoid (
    .clk            (clk),
    .rst_n          (rst_n),
    .i_param_addr   (param_bus_addr),
    .i_param_data   (param_bus_data),
    .i_active       (block_active[4]),
    .i_en           (block_en[4]),
    .o_drive        (block_drive[4])
);

// AWG Block (type 5)
arb_wave u_arb_wave (
    .clk          (clk),
    .rst_n        (rst_n),
    .i_en         (block_en[5]),
    .i_param_data (param_bus_data),
    .i_param_addr (param_bus_addr),
    .i_active     (block_active[5]),
    .o_bram_addr  (awg_r_addr),
    .i_bram_data  (awg_r_data),
    .o_drive      (block_drive[5])
);
    
endmodule

`default_nettype wire
