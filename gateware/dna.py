# (C) Roberr Jordens <jordens@gmail.com> 2014, 2015

from migen.fhdl.std import *
from migen.bank.description import *


class DNA(Module, AutoCSR):
    def __init__(self, version=0b1000001):
        n = 64
        self._r_dna = CSRStatus(n, reset=version << 57)

        ###

        do = Signal()
        cnt = Signal(max=2*n + 1)

        self.specials += Instance("DNA_PORT",
                i_DIN=self._r_dna.status[-1], o_DOUT=do,
                i_CLK=cnt[0], i_READ=cnt < 2, i_SHIFT=1)

        self.sync += [
                If(cnt < 2*n,
                    cnt.eq(cnt + 1),
                    If(cnt[0],
                        self._r_dna.status.eq(Cat(do, self._r_dna.status))
                    )
                )
        ]
