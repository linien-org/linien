`default_nettype none
module linear_ramp #(
    parameter DATA_WIDTH = 32
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  en,
    input  wire [DATA_WIDTH-1:0] i_param_data,
    input  wire [3:0]            i_param_addr,
    input  wire                  i_active,
    output logic signed [13:0]   v_drive
);
    // param 0: v_start  — initial DAC count (signed 14-bit in lower bits)
    // param 1: clk_div  — cycles per +1 step (32-bit unsigned)
    // param 2: duration — NOT seen here, consumed by control FSM

    logic signed [13:0] v_start;
    logic        [31:0] clk_div;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            v_start <= '0;
            clk_div <= 32'd1;
        end else if (en) begin
            case (i_param_addr)
                4'd0: v_start <= i_param_data[13:0];
                4'd1: clk_div <= i_param_data;
            endcase
        end
    end

    // active edge detection
    logic active_ff;
    always_ff @(posedge clk) begin
        if (!rst_n) active_ff <= 1'b0;
        else        active_ff <= i_active;
    end
    logic active_pulse;
    assign active_pulse = i_active & ~active_ff;

    // clock divider
    logic [31:0] counter;
    logic        tick;
    assign tick = (counter == clk_div - 1);

    always_ff @(posedge clk) begin
        if (!rst_n || !active_ff) counter <= '0;
        else                      counter <= tick ? '0 : counter + 1;
    end

    // output
    logic signed [13:0] o_drive_ff;
    always_ff @(posedge clk) begin
        if (!rst_n)          o_drive_ff <= '0;
        else if (active_pulse) o_drive_ff <= v_start;
        else if (active_ff && tick) o_drive_ff <= o_drive_ff + 14'sd1;
    end

    assign v_drive = i_active ? o_drive_ff : '0;

endmodule
`default_nettype wire
