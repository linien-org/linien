"""
regfile_adapter.py - bridges linien's CSR bus to our reg_file and AWG BRAM

the PS (arm cpu) can't talk to reg_file.sv directly because reg_file
is just a plain BRAM with no CSR interface. so this module sits in
between and translates CSR writes into reg_file port A writes.

how it works:
  1. PS writes an address to wr_addr
  2. PS writes data to wr_data
  3. PS writes 1 to wr_strobe
  4. adapter catches the 0->1 edge and pulses wr_en for exactly 1 cycle
  5. reg_file latches the write on that clock edge

same pattern for AWG BRAM but with 10-bit addr and 14-bit data.

also passes through num_blocks (goes to control.sv i_num_blocks) and
enable (goes to ttl_handler.i_enable) since those don't need to go
through reg_file, they're just standalone config values.
"""

from migen import *
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus

class RegFileAdapter(Module, AutoCSR):
    def __init__(self):
        #param reg_file write path
        self.wr_addr = CSRStorage(8, name="wr_addr")
        self.wr_data = CSRStorage(32, name="wr_data")
        self.wr_strobe = CSRStorage(name="wr_strobe")

        self.o_wr_addr = Signal(8, name="o_wr_addr")
        self.o_wr_data = Signal(32, name="o_wr_data")
        self.o_wr_en = Signal(name="o_wr_en")

        strobe_prev = Signal()
        self.sync += strobe_prev.eq(self.wr_strobe.storage)

        self.comb += [
            self.o_wr_addr.eq(self.wr_addr.storage),
            self.o_wr_data.eq(self.wr_data.storage),
            self.o_wr_en.eq(self.wr_strobe.storage & ~strobe_prev),
        ]

        #AWG BRAM write path
        self.awg_addr = CSRStorage(10, name="awg_addr")
        self.awg_data = CSRStorage(14, name="awg_data")
        self.awg_strobe = CSRStorage(name="awg_strobe")

        self.o_awg_addr = Signal(10, name="o_awg_addr")
        self.o_awg_data = Signal(14, name="o_awg_data")
        self.o_awg_en = Signal(name="o_awg_en")

        awg_strobe_prev = Signal()
        self.sync += awg_strobe_prev.eq(self.awg_strobe.storage)

        self.comb += [
            self.o_awg_addr.eq(self.awg_addr.storage),
            self.o_awg_data.eq(self.awg_data.storage),
            self.o_awg_en.eq(self.awg_strobe.storage & ~awg_strobe_prev),
        ]

        #config passthrough
        self.num_blocks = CSRStorage(4, name="num_blocks")
        self.enable = CSRStorage(1, name="enable")

        self.o_num_blocks = Signal(4, name="o_num_blocks")
        self.o_enable = Signal(name="o_enable")

        self.comb += [
            self.o_num_blocks.eq(self.num_blocks.storage),
            self.o_enable.eq(self.enable.storage),
        ]