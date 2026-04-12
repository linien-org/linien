////////////////////////////////////////////////////////////////////////////////
// reg_file.sv — Simple dual-port register file for sequence block parameters
//
// Port A (write): PS/AXI side. The ARM writes block types and parameters here
//                 before the experiment starts. Never written during execution.
// Port B (read):  Control side. The control FSM reads block type and params
//                 during sequence execution. 1-cycle read latency (sync read).
//
// Memory map (stride of 8 per slot, 16 slots):
//   Slot N base = N * 8
//     offset 0:  block type [2:0] (which physical block to activate)
//     offset 1:  param 0
//     offset 2:  param 1
//     offset 3:  param 2
//     offset 4:  param 3
//     offset 5:  param 4
//     offset 6:  param 5
//     offset 7:  param 6
//
//   0x80 (128): num_blocks - 1 (0 = one block, 15 = sixteen blocks)
//   0x81-0xFF:  reserved
//
// Infers simple dual-port BRAM on Xilinx 7-series. No reset for memory
// contents (BRAM doesn't support async reset efficiently). The PS writes
// all relevant addresses before i_start, so uninitialized values are never read.
////////////////////////////////////////////////////////////////////////////////
`default_nettype none
module bram #(
    parameter int ADDR_WIDTH = 8,
    parameter int DATA_WIDTH = 32,

    localparam int DEPTH = 2 ** ADDR_WIDTH
) (
    input wire clk,

    // Port A: write (PS / AXI side, pre-experiment configuration)
    input wire [ADDR_WIDTH-1:0] i_wr_addr,
    input wire [DATA_WIDTH-1:0] i_wr_data,
    input wire                  i_wr_en,

    // Port B: read (control side, 1-cycle latency)
    input wire [ADDR_WIDTH-1:0] i_rd_addr,

    output logic [DATA_WIDTH-1:0] o_rd_data
);

  // Storage
  logic [DATA_WIDTH-1:0] mem[DEPTH];

  // Port A: synchronous write
  always_ff @(posedge clk) begin
    if (i_wr_en) mem[i_wr_addr] <= i_wr_data;
  end

  // Port B: synchronous read (infers BRAM output register)
  always_ff @(posedge clk) begin
    o_rd_data <= mem[i_rd_addr];
  end

endmodule
`default_nettype wire
