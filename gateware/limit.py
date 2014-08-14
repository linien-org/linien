from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR


class Limit(Module, AutoCSR):
    def __init__(self, signal_width=25):
        self.r_minval = CSRStorage(signal_width)
        self.r_maxval = CSRStorage(signal_width)
        self.r_railed = CSRStatus(1)
        minval = Signal((signal_width, True))
        maxval = Signal((signal_width, True))
        self.x = Signal((signal_width, True))
        self.y = Signal((signal_width, True))
        self.railed = Signal()
        self.comb += [
                minval.eq(self.r_minval.storage),
                maxval.eq(self.r_maxval.storage),
                self.r_railed.status.eq(self.railed),
        ]
        self.sync += [
                If(self.x > maxval,
                    self.y.eq(maxval),
                    self.railed.eq(1)
                ).Elif(self.x < minval,
                    self.y.eq(minval),
                    self.railed.eq(1)
                ).Else(
                    self.y.eq(self.x),
                    self.railed.eq(0)
                )
        ]
