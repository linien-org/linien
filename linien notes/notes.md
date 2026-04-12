#### control.sv
- i_start: signal to start the sequence of activations for the function blocks
- i_num_blocks: signal indicating how *many* blocks there are to activate (0 indexed)
- i_init_v_drive: saves the "initial" driving voltage so it can jump back to that
- o_regfile_addr: address provided to the register file to access data
- i_regfile data: data read back from the register file
    - Note how it accoutns for 1-clock cycle latency by including states FETCH_TYPE; provide address to the reg file and LOAD_INIT; loads the... block type?
- i_block_done: signal to indicate that a given block is done (ARBITRATION MUST BE DONE EXTERNALLY)
- i_block_drive: packed array of data from all function blocks (ARBITRATION MUST BE DONE EXTERNALLY)
- o_param_data: shared parameter bus that "programs" the function modules. 
- o_param_addr: MMIO scheme to select which address to write to within a function block
- o_param_wr_en: write enable signal
- o_block_en: enable signal for a given block
- o_block_start: start signal for a given block
- v_drive: signal fed into the DAC (fast/slow chain from MIGEN) to actually drive the output
- o_seq_done: signal to indicate that the sequence is done
- o_active: to indicate the thing is still working. 

#### sinusoid.sv (TODO)
- timing should be responsibility of control block, NOT the function block
- drive output for as long as enable signal is high. 

#### arbitrary_waveform.sv (TODO)
- will step through all 1024 values loaded into the LUT
- includes a clock divider to dicatate how 'fast' it should step through these signals
- FSM/control block/PS will be responsible for determining how "long" to count for/keeping track of driving "active" signals. 
