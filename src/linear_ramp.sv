`default_nettype none
//Linear Ramp block; simple shi
////////////////// Parameters //////////////////
//NOTE: try to avoid any kind of division if possible. 
//0x00: v_start; starting drive voltage
//0x01: v_step; 

module linear_ramp #(
    parameter DATA_WIDTH = 32
) (
    input wire clk,
    input wire rst_n,

    input wire en,
    input wire [DATA_WIDTH-1:0] i_param_data,
    input wire [3:0] i_param_addr,
    input wire i_active,

    output logic signed [13:0] v_drive
);

  //param 0: v_start
  //param 1: v_step
  logic signed [13:0] v_start;
  logic signed [13:0] v_step;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      v_start <= '0;
      v_step  <= '0;
    end else if (en) begin
      case (i_param_addr)
        4'd0: v_start <= i_param_data[13:0];
        4'd1: v_step <= i_param_data[13:0];
      endcase
    end
  end

  logic active_ff;
  always_ff @(posedge clk, negedge rst_n) begin
    if (!rst_n) active_ff <= 1'b0;
    else active_ff <= i_active;
  end

  logic active_pulse;
  assign active_pulse = i_active & ~active_ff;


  logic signed [13:0] o_drive_ff;

  always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) o_drive_ff <= 14'b0;
    else begin
      if (active_pulse) o_drive_ff <= v_start;
      else if (active_ff) begin
        o_drive_ff <= o_drive_ff + v_step;
      end
    end
  end

  assign v_drive = i_active ? o_drive_ff : '0;

endmodule
`default_nettype wire
