from migen.fhdl.std import *
from migen.bank.description import *


class DNA(Module, AutoCSR):
    def __init__(self):
        self.r_dna = CSRStatus(57)

        ###

        d = Signal()
        cnt = Signal(max=flen(self.r_dna.status) + 1)
        rd = Signal(reset=1)
        shift = Signal()

        self.specials += Instance("DNA_PORT",
                i_DI=0, o_DO=d, i_CLK=ClockSignal(),
                i_READ=rd, i_SHIFT=shift)

        self.sync += [
                If(rd,
                    rd.eq(0),
                    shift.eq(1)
                ),
                If(shift & (cnt < flen(self.r_dna.status)),
                    self.r_dna.status.eq(Cat(d, self.r_dna.status)),
                    cnt.eq(cnt + 1)
                )
        ]
