# (C) Roberr Jordens <jordens@gmail.com> 2014, 2015

from migen.fhdl.std import *
from migen.bank.description import *
from migen.genlib.cdc import MultiReg


class Gpio(Module, AutoCSR):
    def __init__(self, pins):
        n = flen(pins)
        self.i = Signal(n)
        self.o = Signal(n)
        self._in = CSRStatus(n)
        self._out = CSRStorage(n)
        self._oe = CSRStorage(n)

        ###

        t = [TSTriple(1) for i in range(n)]
        self.specials += [ti.get_tristate(pins[i]) for i, ti in enumerate(t)]
        self.specials += MultiReg(Cat([ti.i for ti in t]), self.i)
        self.comb += [
                Cat([ti.o for ti in t]).eq(self._out.storage | self.o),
                Cat([ti.oe for ti in t]).eq(self._oe.storage),
                self._in.status.eq(self.i),
        ]
