# (C) Roberr Jordens <jordens@gmail.com> 2014, 2015

from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR


class Filter(Module, AutoCSR):
    def __init__(self, width):
        self.x = Signal((width, True))
        self.y = Signal((width, True))

        self.hold = Signal()
        self.clear = Signal()
        self.error = Signal()

        if False:
            self._y = CSRStatus(width)
            self.comb += self._y.status.eq(self.y)
