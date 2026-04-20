/* Machine-generated using Migen */
module top(
	input sys_clk,
	input sys_rst
);

reg [7:0] regfileadapter_csrstorage0 = 8'd0;
reg [31:0] regfileadapter_csrstorage1 = 32'd0;
reg regfileadapter_csrstorage2 = 1'd0;
wire [7:0] regfileadapter_o_wr_addr;
wire [31:0] regfileadapter_o_wr_data;
wire regfileadapter_o_wr_en;
reg regfileadapter0 = 1'd0;
reg [9:0] regfileadapter_csrstorage3 = 10'd0;
reg [13:0] regfileadapter_csrstorage4 = 14'd0;
reg regfileadapter_csrstorage5 = 1'd0;
wire [9:0] regfileadapter_o_awg_addr;
wire [13:0] regfileadapter_o_awg_data;
wire regfileadapter_o_awg_en;
reg regfileadapter1 = 1'd0;
reg [3:0] regfileadapter_csrstorage6 = 4'd0;
reg regfileadapter_csrstorage7 = 1'd0;
wire [3:0] regfileadapter_o_num_blocks;
wire regfileadapter_o_enable;

// synthesis translate_off
reg dummy_s;
initial dummy_s <= 1'd0;
// synthesis translate_on

assign regfileadapter_o_wr_addr = regfileadapter_csrstorage0;
assign regfileadapter_o_wr_data = regfileadapter_csrstorage1;
assign regfileadapter_o_wr_en = (regfileadapter_csrstorage2 & (~regfileadapter0));
assign regfileadapter_o_awg_addr = regfileadapter_csrstorage3;
assign regfileadapter_o_awg_data = regfileadapter_csrstorage4;
assign regfileadapter_o_awg_en = (regfileadapter_csrstorage5 & (~regfileadapter1));
assign regfileadapter_o_num_blocks = regfileadapter_csrstorage6;
assign regfileadapter_o_enable = regfileadapter_csrstorage7;

always @(posedge sys_clk) begin
	regfileadapter0 <= regfileadapter_csrstorage2;
	regfileadapter1 <= regfileadapter_csrstorage5;
	if (sys_rst) begin
		regfileadapter0 <= 1'd0;
		regfileadapter1 <= 1'd0;
	end
end

endmodule
