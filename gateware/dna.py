from migen.fhdl.std import *
from migen.bank.description import *


class DNA(Module, AutoCSR):
    def __init__(self):
        self.r_dna = CSRStatus(57)

        ###

        d = Signal()
        n = flen(self.r_dna.status)
        rd = Signal(reset=1)
        so = Signal()
        si = Signal()
        cnt = Signal(max=n + 1, reset=n)

        self.specials += Instance("DNA_PORT",
                i_DIN=d, o_DOUT=d, i_CLK=ClockSignal(),
                i_READ=rd, i_SHIFT=so)

        self.comb += so.eq(~rd & (cnt > 0))
        self.sync += [
                If(rd,
                    rd.eq(0)
                ),
                If(so,
                    cnt.eq(cnt - 1),
                ),
                si.eq(so),
                If(si,
                    self.r_dna.status.eq(Cat(self.r_dna.status[1:], d)),
                )
        ]
