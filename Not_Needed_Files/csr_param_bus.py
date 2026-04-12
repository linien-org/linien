"""
csr_param_bus.py - shared parameter bus for sequence block configuration

the PS writes block parameters one at a time through a shared bus:
  1. set block_sel (which block, 0-15)
  2. set param_addr (which parameter within that block, 0-5)
  3. set param_data (32-bit value)
  4. pulse param_write (latch it)

internally this module stores a 16×6 array of 32-bit registers.
the FSM reads parameters for a given block by asserting read_block_sel,
and the outputs present that block's full parameter set combinationally.

parameter address map (same slots for all block types, interpreted differently):
  addr 0: BLOCK_TYPE  (0=delay, 1=ramp, 2=jump, 3=overdrive, 4=chirp, 5=sine, 6=awg)
  addr 1: DURATION    (24-bit, clock cycles)
  addr 2: PARAM_A     (ramp: start_v, jump: target, chirp: start_freq, sine: freq, awg: clk_div)
  addr 3: PARAM_B     (ramp: step_size, chirp: end_freq, sine: amplitude, awg: wfm_length)
  addr 4: PARAM_C     (ramp: target_v, chirp: amplitude, sine: dc_offset)
  addr 5: PARAM_D     (chirp: dc_offset, overdrive: overshoot_amount)
"""

from migen import *


# constants
MAX_BLOCKS = 16
PARAMS_PER_BLOCK = 6
DATA_WIDTH = 32

# parameter addresses
ADDR_BLOCK_TYPE = 0
ADDR_DURATION = 1
ADDR_PARAM_A = 2
ADDR_PARAM_B = 3
ADDR_PARAM_C = 4
ADDR_PARAM_D = 5


class CSRParamBus(Module):
    def __init__(self):
        # PS write interface (directly from CSR registers)
        self.i_block_sel = Signal(4, name="i_block_sel")      # which block (0-15)
        self.i_param_addr = Signal(3, name="i_param_addr")    # which param (0-5)
        self.i_param_data = Signal(DATA_WIDTH, name="i_param_data")  # value
        self.i_param_write = Signal(name="i_param_write")     # write strobe


        # FSM read interface
        self.i_read_block_sel = Signal(4, name="i_read_block_sel")  # FSM asks for this block

        # full parameter set for the selected block (combinational read)
        self.o_block_type = Signal(3, name="o_block_type")
        self.o_duration = Signal(24, name="o_duration")
        self.o_param_a = Signal(DATA_WIDTH, name="o_param_a")
        self.o_param_b = Signal(DATA_WIDTH, name="o_param_b")
        self.o_param_c = Signal(DATA_WIDTH, name="o_param_c")
        self.o_param_d = Signal(DATA_WIDTH, name="o_param_d")

        # num_blocks: how many blocks in the sequence (PS writes this)
        self.i_num_blocks = Signal(4, name="i_num_blocks")
        self.o_num_blocks = Signal(4, name="o_num_blocks")


        # storage: 16 blocks × 6 params × 32 bits
        # migen Array of Arrays. outer index = block, inner index = param.
        self.storage = Array(
            Array(Signal(DATA_WIDTH, name=f"blk{b}_p{p}") for p in range(PARAMS_PER_BLOCK))
            for b in range(MAX_BLOCKS)
        )


        # write logic
        # when i_param_write is pulsed, latch i_param_data into
        # storage[i_block_sel][i_param_addr].
        #
        # this happens on the clock edge, so the PS can set up
        # block_sel + addr + data on one cycle, then pulse write
        # on the next cycle. standard CSR write pattern.

        self.sync += [
            If(self.i_param_write,
                self.storage[self.i_block_sel][self.i_param_addr].eq(
                    self.i_param_data
                ),
            )
        ]

        # read logic (combinational)
        # the FSM sets i_read_block_sel, and all 6 params for that
        # block appear on the outputs in the same cycle. no latency.
        #
        # block_type is only 3 bits (0-6), duration is 24 bits.
        # we store full 32-bit values and slice on output.

        self.comb += [
            self.o_block_type.eq(
                self.storage[self.i_read_block_sel][ADDR_BLOCK_TYPE][:3]
            ),
            self.o_duration.eq(
                self.storage[self.i_read_block_sel][ADDR_DURATION][:24]
            ),
            self.o_param_a.eq(
                self.storage[self.i_read_block_sel][ADDR_PARAM_A]
            ),
            self.o_param_b.eq(
                self.storage[self.i_read_block_sel][ADDR_PARAM_B]
            ),
            self.o_param_c.eq(
                self.storage[self.i_read_block_sel][ADDR_PARAM_C]
            ),
            self.o_param_d.eq(
                self.storage[self.i_read_block_sel][ADDR_PARAM_D]
            ),
            self.o_num_blocks.eq(self.i_num_blocks),
        ]
