# Robert Jordens <jordens@gmail.com> 2014

from collections import OrderedDict

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *
from migen.fhdl.bitcontainer import bits_for
from migen.genlib.cordic import Cordic

from .filter import Filter
from .iir import Iir
from .limit import LimitCSR
from .sweep import SweepCSR
from .relock import Relock
from .modulate import Modulate, Demodulate


signal_width = 25
coeff_width = 18


class SatAdd(Module):
    def __init__(self, width, *x):
        self.y = Signal((width, True))

        guard = log2_int(len(x), need_pow2=False)
        sum = Signal((width + guard, True))
        lim = 1<<(width - 1)
        self.comb += [
                sum.eq(optree("+", x)),
                If(sum > lim - 1,
                    self.y.eq(lim - 1),
                ).Elif(sum < -lim,
                    self.y.eq(-lim),
                ).Else(
                    self.y.eq(sum),
                )
        ]


class InChain(Filter):
    def __init__(self, width=14):
        Filter.__init__(self, width=signal_width)
        self.adc = Signal((width, True))
        self.submodules.limit = LimitCSR(width=signal_width)
        self.submodules.iir = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.demod = Demodulate(width=signal_width)

        self.r_tap = CSRStorage(2, reset=0)
        self.r_adc = CSRStatus(width)

        ###

        ys = Array([self.x, self.limit.y, self.iir.y, self.demod.y])
        self.comb += [
                self.x.eq(self.adc << (signal_width - width)),
                self.limit.x.eq(self.x),
                self.iir.x.eq(self.limit.y),
        ]
        self.sync += [
                self.r_adc.status.eq(self.adc),
                self.demod.x.eq(self.iir.y),
                self.y.eq(ys[self.r_tap.storage])
        ]


class OutChain(Filter):
    def __init__(self, width=14):
        Filter.__init__(self, width=signal_width)
        self.r = Signal((signal_width, True))
        self.submodules.iir_a = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.iir_b = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.iir_c = Iir(width=signal_width,
                coeff_width=coeff_width, order=2)
        self.submodules.iir_d = Iir(width=signal_width,
                coeff_width=coeff_width, order=2)
        self.submodules.relock = Relock(width=signal_width)
        self.submodules.sweep = SweepCSR(width=signal_width)
        self.submodules.mod = Modulate(width=signal_width)
        self.submodules.limit = LimitCSR(width=signal_width)
        self.dac = Signal((width, True))

        self.r_tap = CSRStorage(3, reset=0)
        self.r_relock = CSRStorage(3)
        self.r_dac = CSRStatus(width)

        ys = Array([self.x, self.iir_a.y, self.iir_b.y,
            self.iir_c.y, self.iir_d.y])
        self.submodules.sat = SatAdd(signal_width, 
                self.relock.y, self.sweep.y, self.mod.y,
                self.y)
        self.comb += [
                self.relock.x.eq(self.r),
                self.limit.x.eq(self.sat.y),
                self.dac.eq(self.limit.y >> (signal_width - width)),
        ]
        self.sync += [
                self.r_dac.status.eq(self.dac),
                self.iir_a.x.eq(self.x),
                self.iir_b.x.eq(self.iir_a.y),
                self.iir_c.x.eq(self.iir_b.x),
                self.iir_d.x.eq(self.iir_c.x),
                self.y.eq(ys[self.r_tap.storage]),
        ]


class Pid(Module, AutoCSR):
    def __init__(self):
        self.r_version = CSRStatus(8)
        self.r_version.status.reset = 1

        self.submodules.in_a = InChain(14)
        self.submodules.in_b = InChain(14)
        self.submodules.out_a = OutChain(14)
        self.submodules.out_b = OutChain(14)

        self.r_tap_a = CSRStorage(2, reset=0b00)
        self.r_tap_b = CSRStorage(2, reset=0b00)
        self.comb += [
                self.out_a.x.eq(
                    Mux(self.r_tap_a.storage[0], self.in_a.y, 0) +
                    Mux(self.r_tap_a.storage[1], self.in_b.y, 0)),
                self.out_b.x.eq(
                    Mux(self.r_tap_b.storage[0], self.in_a.y, 0) +
                    Mux(self.r_tap_b.storage[1], self.in_b.y, 0)),
        ]

