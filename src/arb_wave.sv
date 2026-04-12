`default_nettype none
//0x00: clk_div: value for the clock divider
//into it
module arb_wave (
    input wire [3:0] i_param_addr,
    input wire [31:0] i_param_data,
    input wire i_en,
    input wire i_active,
    input wire rst_n,
    input wire clk,

    //BRAM ABSTRACTION
    output logic [ 9:0] o_bram_addr,
    input  wire  [13:0] i_bram_data,

    output logic signed [13:0] o_drive
);

  //param loading

  logic [31:0] clk_div;
  always_ff @(posedge clk, negedge rst_n) begin
    if (!rst_n) begin
      clk_div <= 32'd1;  // default: step every cycle
    end else if (i_en && i_param_addr == 4'd0) begin
      clk_div <= i_param_data;
    end
  end

  logic active_ff;

  always_ff @(posedge clk, negedge rst_n) begin
    if (!rst_n) active_ff <= 1'b0;
    else active_ff <= i_active;
  end
  logic active_pulse;
  assign active_pulse = i_active & ~active_ff;

  //clock divider logic
  logic [31:0] div_counter;
  logic [ 9:0] bram_addr_r;

  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) begin
      div_counter <= 32'b0;
      bram_addr_r <= 10'b0;
    end else if (~i_active) begin
      div_counter <= 32'b0;
      bram_addr_r <= 10'b0;
    end else begin
      if (div_counter == clk_div - 1) begin
        div_counter <= 32'b0;
        if (bram_addr_r != 10'd1023) bram_addr_r <= bram_addr_r + 1;
      end else begin
        div_counter <= div_counter + 1'b1;
      end
    end
  end

  assign o_bram_addr = bram_addr_r;

  //output pipeline stage; accounting for 1 clock cycle BRAM read latency
  //use active_ff (delayed by 1 cycle) so BRAM output is valid before we sample it
  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) o_drive <= 14'b0;
    else if (~active_ff) o_drive <= 14'b0;
    else o_drive <= i_bram_data;
  end


endmodule
`default_nettype wire
