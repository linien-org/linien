
module ROM #(
  parameter string FILE="",
  parameter int DATA_WIDTH=14,
  parameter int ADDR_WIDTH=9
  )(
    input wire clk,
    input [ADDR_WIDTH-1:0] i_rd_addr,
    output logic [DATA_WIDTH-1:0] o_rd_data
    );

    localparam int DEPTH=2**ADDR_WIDTH;
    (* ram_style = "block" *) logic [DATA_WIDTH-1:0] mem [DEPTH];

    initial begin
    $readmemh(FILE, mem);
    end

    always_ff@(posedge clk)begin
      o_rd_data<=mem[i_rd_addr];
    end
    endmodule

