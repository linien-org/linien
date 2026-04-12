module sinusoid_tb ();

  logic [3:0] i_param_addr;
  logic [31:0] i_param_data;
  logic i_en;
  logic i_active;
  logic rst_n;
  logic clk;

  logic signed [13:0] o_drive;

  //VERIFIED THAT IT READS IN THE MEMH FILE!
  initial begin
    $dumpfile("sinusoid_tb.vcd");
    $dumpvars(0, sinusoid_tb);
  end
  sinusoid #(.DATA_WIDTH(32)) iDUT (
      .i_param_addr(i_param_addr),
      .i_param_data(i_param_data),
      .i_en(i_en),
      .i_active(i_active),
      .rst_n(rst_n),
      .clk(clk),
      .o_drive(o_drive)
  );

endmodule
