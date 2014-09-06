from migen.fhdl.std import *
from migen.bank.description import *


class DNA(Module, AutoCSR):
    def __init__(self, version=0b1000001):
        n = 64
        self._r_dna = CSRStatus(n, reset=version << 57)

        ###

        do = Signal()
        cnt = Signal(max=2*n + 1)
        dna = Signal(n)

        self.specials += Instance("DNA_PORT",
                i_DIN=dna[-1], o_DOUT=do,
                i_CLK=cnt[0], i_READ=cnt < 2, i_SHIFT=1)

        self.comb += self._r_dna.status.eq(dna)
        self.sync += [
                If(cnt < 2*n,
                    cnt.eq(cnt + 1),
                    If(cnt[0],
                        Cat(dna).eq(Cat(do, dna))
                    )
                )
        ]
