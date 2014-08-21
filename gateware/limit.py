from migen.fhdl.std import *
from migen.bank.description import CSRStorage

from .filter import Filter


class Limit(Module):
    def __init__(self, width):
        self.x = Signal((width, True))
        self.y = Signal.like(self.x)
        self.max = Signal.like(self.x)
        self.min = Signal.like(self.x)
        self.railed = Signal()

        ###

        self.comb += [
                If(self.x >= self.max,
                    self.y.eq(self.max),
                    self.railed.eq(1)
                ).Elif(self.x <= self.min,
                    self.y.eq(self.min),
                    self.railed.eq(1)
                ).Else(
                    self.y.eq(self.x),
                    self.railed.eq(0)
                )
        ]


class LimitCSR(Filter):
    def __init__(self, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        self.r_min = CSRStorage(width, reset=1<<width - 1)
        self.r_max = CSRStorage(width, reset=(1<<width - 1) - 1)

        ###
        
        self.submodules.limit = Limit(width)

        self.comb += [
                self.limit.x.eq(self.x),
        ]
        self.sync += [
                self.limit.min.eq(self.r_min.storage),
                self.limit.max.eq(self.r_max.storage),
                self.y.eq(self.limit.y),
                self.error.eq(self.limit.railed)
        ]
