from migen.fhdl.std import *
from migen.bank.description import *
from migen.genlib.cdc import MultiReg


class Gpio(Module, AutoCSR):
    def __init__(self, pins):
        n = flen(pins)
        self.i = Signal(n)
        self.o = Signal(n)
        self._r_in = CSRStatus(n)
        self._r_out = CSRStorage(n)
        self._r_oe = CSRStorage(n)

        ###

        t = [TSTriple(1) for i in range(n)]
        self.specials += [ti.get_tristate(pins[i]) for i, ti in enumerate(t)]
        self.specials += MultiReg(Cat([ti.i for ti in t]), self.i)
        self.comb += [
                Cat([ti.o for ti in t]).eq(self._r_out.storage | self.o),
                Cat([ti.oe for ti in t]).eq(self._r_oe.storage),
                self._r_in.status.eq(self.i),
        ]
