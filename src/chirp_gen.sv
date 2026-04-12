`default_nettype none
//0x00 = this is the address for the parameter a
//0x01 = this is the address for the parameter b
//0x02 = this is the address for the parameter rate
//0x03 = this is the address for the parameter raterate

module chirp_gen (
    input wire clk,
    input wire rst_n,
    input wire [3:0] i_param_addr,        // fixed: 4-bit to match control.sv
    input wire [31:0] i_param_data,
    input wire en,                         // o_block_en — latch params
    input wire active,                     // o_block_active — drive output

    output logic signed [13:0] voltage     // fixed: signed 14-bit
);

logic signed [31:0] cur_rate;
logic signed [31:0] a;
logic signed [31:0] b;
logic signed [31:0] rate;
logic signed [31:0] raterate;

// param loading
always_ff @(posedge clk) begin
    if (!rst_n) begin                      
        a        <= '0;
        b        <= '0;
        rate     <= '0;
        raterate <= '0;
    end else if (en) begin                 // only during param loading
        case (i_param_addr)                // fixed: case instead of unique case
            4'd0: a        <= i_param_data;
            4'd1: b        <= i_param_data;
            4'd2: rate     <= i_param_data;
            4'd3: raterate <= i_param_data;
            default: ;                     // fixed: added default
        endcase
    end
end

// execution
logic signed [31:0] cur_voltage;
logic active_prev;

always_ff @(posedge clk) begin
    if (!rst_n) begin                      // fixed: !rst_n
        cur_voltage <= '0;
        cur_rate    <= '0;
        active_prev <= 1'b0;
    end else begin
        active_prev <= active;

        if (active && !active_prev) begin  // fixed: load on rising edge of active
            cur_voltage <= a;
            cur_rate    <= rate;
        end else if (active) begin         // fixed: only run when active
            cur_rate    <= cur_rate + raterate;
            cur_voltage <= cur_voltage + cur_rate;
        end
    end
end

// output with clamping                    // fixed: clamp instead of truncate
always_comb begin
    if (!active)
        voltage = '0;                      // fixed: zero when inactive
    else if (cur_voltage > 32'sh1FFF)       // 8191 in hex
        voltage = 14'sh1FFF;
    else if (cur_voltage < -32'sh2000)      // -8192 in hex
        voltage = -14'sh2000;
    else
        voltage = cur_voltage[13:0];
end

endmodule
`default_nettype wire