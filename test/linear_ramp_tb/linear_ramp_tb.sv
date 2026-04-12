module linear_ramp_tb();

localparam DATA_WIDTH=32;
     logic clk;
     logic rst_n;

     logic en;
     logic [DATA_WIDTH-1:0] i_param_data;
     logic [3:0] i_param_addr;
     logic i_active;

     logic signed [13:0] v_drive;
  initial begin
    $dumpfile("linear_ramp_tb.vcd");
    $dumpvars(0, linear_ramp_tb);
  end

     linear_ramp iDUT(
       .clk(clk),
       .rst_n(rst_n),
       .en(en),
       .i_param_data(i_param_data),
       .i_param_addr(i_param_addr),
       .i_active(i_active),
       .v_drive(v_drive)
       );
endmodule

