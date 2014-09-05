from migen.fhdl.std import *
from migen.bank.description import CSRStorage
from migen.genlib.cordic import Cordic

from .filter import Filter


class Demodulate(Filter):
    def __init__(self, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        self.r_phase = CSRStorage(width)
        self.phase = Signal(width)

        self.submodules.cordic = Cordic(width=width + 1, stages=width + 1,
                guard=2,
                eval_mode="pipelined", cordic_mode="rotate",
                func_mode="circular")
        self.comb += [
                self.cordic.xi.eq(self.x),
                self.cordic.zi.eq((self.phase + self.r_phase.storage) << 1),
                self.y.eq(self.cordic.xo >> 1)
        ]


class Modulate(Filter):
    def __init__(self, freq_width=32, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        self.r_amp = CSRStorage(width)
        self.r_freq = CSRStorage(freq_width)
        self.phase = Signal(width)

        z = Signal(freq_width)
        stop = Signal()
        self.sync += [
                stop.eq(self.r_freq.storage == 0),
                If(stop,
                    z.eq(0)
                ).Else(
                    z.eq(z + self.r_freq.storage)
                )
        ]

        self.submodules.cordic = Cordic(width=width + 1, stages=width + 1,
                guard=2,
                eval_mode="pipelined", cordic_mode="rotate",
                func_mode="circular")
        self.comb += [
                self.phase.eq(z[-flen(self.phase):]),
                self.cordic.xi.eq(self.r_amp.storage + self.x),
                self.cordic.zi.eq(self.phase << 1),
                self.y.eq(self.cordic.xo >> 1)
        ]
