from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR


class Filter(Module, AutoCSR):
    def __init__(self, width):
        self.x = Signal((width, True))
        self.y = Signal((width, True))

        self.mode_in = Signal(4) # ce_in, ce_out, rst_in, rst_out
        self.mode_out = Signal(4)
        self.mode = Signal(4)

        self.r_cmd = CSRStorage(4)
        self.r_mask = CSRStorage(4)
        self.r_mode = CSRStatus(4)

        ###

        self.comb += [
                self.r_mode.status.eq(self.mode_out)
        ]
        self.sync += [
                self.mode.eq((self.mode_in & ~self.r_mask.storage) |
                    self.r_cmd.storage),
        ]
