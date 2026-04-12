`default_nettype none
module delay #(
  parameter DATA_WIDTH = 32
)(
    input wire clk,
    input wire rst_n,

    input wire en,        //connects to o_block_en in control
    input wire [DATA_WIDTH-1:0] i_param_data,
    input wire [3:0]            i_param_addr,
    input wire             active,    //connects to o_block_active in control

    output logic [13:0] v_drive
);
  // info about parameters:
  //     param 1: first 13 bits = v_from
  //     param 2: 
  logic [13:0] v_prev;
  
  always_ff @ (posedge clk) begin
    if (!rst_n) 
      v_prev <= '0;
    else if (en && i_param_addr == 4'd0) begin
      v_prev <= i_param_data[13:0];
    end
  end
  
  assign v_drive = active ? v_prev : '0;
endmodule
`default_nettype wire