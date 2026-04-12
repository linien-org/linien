//Sinusoid generator; simple block, for testing generation and simulation of
//waveforms?
////////////////// Parameters //////////////////
//0x00:v_mid; middle value (i.e, DC offset)
//0x01:v_amp; amplitude of sinusoid
//0x02: v_min_cutoff; minimum cutoff voltge
//0x03: v_max_cutoff; maximum cutoff voltge
//0x04: phase_increment; phase_increment for the sin generator; indexes into
//14x1024 LUT for values.
//
//TODO CHANGES: remove the timer, and instead rely on an external "i_drive"
//signal

module sinusoid #(
    parameter DATA_WIDTH
  )(
    input wire [3:0] i_param_addr,
    input wire [31:0] i_param_data,
    input wire i_en,
    input wire i_active,
    input wire rst_n,
    input wire clk,

    output logic signed [13:0] o_drive
);

  wire [31:0] v_mid;
  wire [31:0] v_amp;
  wire [31:0] v_min_cut;
  wire [31:0] v_max_cut;
  wire [31:0] phase_increment;

  logic [31:0] params[4:0];

  assign v_mid = params[0];
  assign v_amp = params[1];
  assign v_min_cut = params[2];
  assign v_max_cut = params[3];
  assign phase_increment = params[4];


  always @(posedge clk, negedge rst_n) begin
    if (~rst_n) begin
      for (integer i = 0; i < 5; i = i + 1) begin
        params[i] <= 32'b0;
      end
    end else begin
      //if this block is enabled and i_wren is high, load in the value
      if (i_en) begin
        //only allow values to be read in if in the range of parameters AND 
        //not being currently driven. 
        if (i_param_addr <= 4'h4 && i_active==1'b0) begin
          params[i_param_addr] <= i_param_data;
        end  //otherwise, ignore
        else begin
        end
      end
    end
  end

  // logicisters to keep track of current driving voltage and current phase

  //////////////////// THEORY: Numerically contlle oscillators and phase accumulators ////////////////////
  //sin wave is simply sim(phi), where phi is the phase, between 0 and 2*pi
  //repeatedly.
  //a sin wave of frequency f implies that the phase phi increases by 2*pi*f
  //(or 2*pi/t,t=1/f) radians per second.
  //at every clock cycle, the phase should increase by 2*pi*f*T_clk
  //
  //2*pi cant be stored in logicisters, so map 0->2*pi to the full range of an
  //N bit integer, 0->2^N. Phase accumulator is in "integer phase units"
  //for a 32 bit accumulator, a full circle is 2^32
  //hence phase increment becomes (f_desired/f_clk)*2^32
  //possibly add other LUT's to work with?

  logic [31:0] phase_accum;
  logic signed [13:0] sin_LUT[1023:0];
  initial begin
    $readmemh("sin_lut.memh", sin_LUT);
  end


  logic active_ff;
  always @(posedge clk, negedge rst_n) begin
    if (~rst_n) active_ff <= 1'b0;
    else active_ff <= i_active;
  end

  logic active_pulse;
  assign active_pulse = i_active & ~active_ff;
  //o_done will be a pulse(?)

  always @(posedge clk, negedge rst_n) begin
    if (~rst_n) phase_accum <= 32'b0;
    else if(i_active==1'b0) phase_accum<=32'b0;
    else begin
      if (i_active == 1'b1) begin
        phase_accum <= phase_accum + phase_increment;
      end  //while in the idle state, reset back to 0; dont maintain previous phase?
    end
  end

  //Note: sin_LUT stores signed values of sin, from -2^13 to 2^13, 
  //representing -1 to 1 normalized. 
  //v_amp scales it, v_mid shifts it. 
  logic signed [13:0] lut_raw;
  logic signed [31:0] raw_out;
  wire signed  [31:0] v_mid_s = $signed(v_mid);
  wire signed  [31:0] v_amp_s = $signed(v_amp);
  wire signed  [31:0] v_min_cut_s = $signed(v_min_cut);
  wire signed  [31:0] v_max_cut_s = $signed(v_max_cut);

  // Stage 1: LUT lookup (registered)
logic signed [13:0] lut_reg;
always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) lut_reg <= '0;
    else if (i_active) lut_reg <= sin_LUT[phase_accum[31:22]];
    else lut_reg <= '0;
end

// Stage 2: multiply (registered)
logic signed [31:0] mult_reg;
always_ff @(posedge clk, negedge rst_n) begin
    if (~rst_n) mult_reg <= '0;
    else if (i_active) mult_reg <= lut_reg * v_amp_s;
    else mult_reg <= '0;
end

// Stage 3: add + clamp (combinational)
always_comb begin
    raw_out = v_mid_s + (mult_reg >>> 13);
    o_drive = (!i_active) ? '0 :
              (raw_out > v_max_cut_s) ? v_max_cut_s[13:0] :
              (raw_out < v_min_cut_s) ? v_min_cut_s[13:0] :
              raw_out[13:0];
end
endmodule

