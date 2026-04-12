module arb_wave_tb ();

  localparam ADDR_WIDTH = 10;
  localparam DATA_WIDTH = 14;
  logic clk;
  logic rst_n;

  logic i_en;
  logic [31:0] i_param_data;
  logic [3:0] i_param_addr;
  logic i_active;

  logic signed [13:0] v_drive;

  logic [9:0] o_bram_addr;
  logic signed [13:0] i_bram_data;

  initial begin
    $dumpfile("arb_wave_tb.vcd");
    $dumpvars(0, arb_wave_tb);
  end


  logic        [ADDR_WIDTH-1:0] i_wr_addr;
  logic        [DATA_WIDTH-1:0] i_wr_data;
  logic                         i_wr_en;
  logic        [ADDR_WIDTH-1:0] i_rd_addr;
  logic        [DATA_WIDTH-1:0] o_rd_data;
  logic signed [          13:0] o_drive;
  /////////TREAT THE FSM_REG PREVIOUSLY DESIGNED AS A PLACEHOLDER FOR 
  //IP INSTANTIATED BRAM BLOCK WITH AXI BUS
  bram #(
      .ADDR_WIDTH(10),
      .DATA_WIDTH(14)
  ) BRAM (
      .clk(clk),
      .i_wr_addr(i_wr_addr),
      .i_wr_data(i_wr_data),
      .i_wr_en(i_wr_en),
      .i_rd_addr(o_bram_addr),
      .o_rd_data(i_bram_data)
  );

  arb_wave iDUT (
      .clk(clk),
      .rst_n(rst_n),
      .i_en(i_en),
      .i_param_data(i_param_data),
      .i_param_addr(i_param_addr),
      .i_active(i_active),
      .o_drive(o_drive),
      .o_bram_addr(o_bram_addr),
      .i_bram_data(i_bram_data)
  );
endmodule


