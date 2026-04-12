module chirp_gen_tb();

// Declare signals FIRST
logic clk;
logic rst;
logic [3:0] i_param_addr;
logic [31:0] i_param_data;
logic start;
logic active;

logic signed [13:0] voltage;

// DUT instantiation AFTER declarations
chirp_gen idut(
    .clk(clk),
    .rst_n(rst),
    .i_param_addr(i_param_addr),
    .i_param_data(i_param_data),
    .en(start),
    .active(active),

    .voltage(voltage)
);


// Stimulus
initial begin
    clk = 0;
    rst = 0;       // assert reset (active-low: 0 = in reset)
    start = 0;
    active = 0;
    i_param_addr = 4'd0;
    i_param_data = 32'h0;

    @(posedge clk);
    @(posedge clk);
    rst = 1;       // deassert reset (active-low: 1 = normal operation)
    @(posedge clk);

    // Load parameters while en=1
    start = 1;
    i_param_addr = 4'd0;
    i_param_data = 32'h00000000;   // a
    @(posedge clk);
    i_param_addr = 4'd1;
    i_param_data = 32'h00001000;   // b
    @(posedge clk);
    i_param_addr = 4'd2;
    i_param_data = 32'h00000000;   // rate
    @(posedge clk);
    i_param_addr = 4'd3;
    i_param_data = 32'h00000001;   // raterate
    @(posedge clk);

    start = 0;

    // Activate chirp execution
    active = 1;
    @(posedge clk);

    #100000; // wait for some time to observe the output

$finish;


end

// Clock generation
always #1 clk = ~clk;

endmodule