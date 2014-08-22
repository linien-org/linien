# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *

from .filter import Filter
from .iir import Iir
from .limit import LimitCSR
from .sweep import SweepCSR
from .relock import Relock
from .modulate import Modulate, Demodulate


signal_width = 25
coeff_width = 18


class InChain(Filter):
    def __init__(self, width=14):
        Filter.__init__(self, width=signal_width)

        self.adc = Signal((width, True))
        self.submodules.limit = LimitCSR(width=signal_width)
        self.submodules.iir_a = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.demod = Demodulate(width=signal_width)

        self.r_tap = CSRStorage(2, reset=0)
        self.r_adc = CSRStatus(width)

        ###

        ys = Array([self.x, self.limit.y, self.iir_a.y, self.demod.y])
        self.comb += [
                self.r_adc.status.eq(self.adc),
                self.x[-width:].eq(self.adc),
                self.limit.x.eq(self.x),

                self.limit.hold_in.eq(self.hold),
                self.iir_a.hold_in.eq(self.hold),
                self.demod.hold_in.eq(self.hold),
                self.limit.clear_in.eq(self.clear),
                self.iir_a.clear_in.eq(self.clear),
                self.demod.clear_in.eq(self.clear),
        ]
        self.sync += [
                self.iir_a.x.eq(self.limit.y),
                self.demod.x.eq(self.iir_a.y),
                self.y.eq(ys[self.r_tap.storage])
        ]


class OutChain(Filter):
    def __init__(self, width=14):
        Filter.__init__(self, width=signal_width)

        self.submodules.iir_a = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.iir_b = Iir(width=signal_width,
                coeff_width=coeff_width, order=2)
        self.submodules.iir_c = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
#        self.submodules.iir_d = Iir(width=signal_width*2-1,
#                coeff_width=2*coeff_width-1, order=2, mode="iterative")
        self.submodules.iir_d = Iir(width=signal_width,
                coeff_width=coeff_width, order=2)

        self.submodules.relock = Relock(width=signal_width)
        self.submodules.sweep = SweepCSR(width=signal_width)
        self.submodules.mod = Modulate(width=signal_width)
        self.asg = Signal((width, True))
        self.submodules.limit = LimitCSR(width=signal_width, guard=3)
        self.dac = Signal((width, True))

        self.r_tap = CSRStorage(3, reset=0)
        self.r_dac = CSRStatus(width)

        ya = Signal((signal_width + 1, True))
        yb = Signal((signal_width + 1, True))
        y1 = Signal((signal_width + 2, True))
        ys = Array([self.x, self.iir_a.y, self.iir_b.y,
            self.iir_c.y, self.iir_d.y[-signal_width:]])
        self.comb += [
                self.clear_in.eq(self.limit.error),
                self.iir_a.clear_in.eq(self.clear),
                self.iir_b.clear_in.eq(self.clear),
                self.iir_c.clear_in.eq(self.clear),
                self.iir_d.clear_in.eq(self.clear),
                #self.sweep.clear_in.eq(self.clear),
                #self.mod.clear_in.eq(self.clear),
                self.relock.clear_in.eq(self.limit.error),

                self.hold_in.eq(self.relock.error),
                self.iir_a.hold_in.eq(self.hold),
                self.iir_b.hold_in.eq(self.hold),
                self.iir_c.hold_in.eq(self.hold),
                self.iir_d.hold_in.eq(self.hold),
                #self.sweep.hold_in.eq(self.hold),
                #self.mod.hold_in.eq(self.hold),
                #self.relock.hold_in.eq(self.hold),

                self.r_dac.status.eq(self.dac),
        ]
        self.sync += [
                self.iir_a.x.eq(self.x),
                self.iir_b.x.eq(self.iir_a.y),
                self.iir_c.x.eq(self.iir_b.y),
                self.iir_d.x[-signal_width:].eq(self.iir_c.y),
                ya.eq(self.sweep.y + (self.asg<<(signal_width - width))),
                yb.eq(self.relock.y + self.mod.y),
                y1.eq(ya + yb),
                self.y.eq(ys[self.r_tap.storage]),
                self.limit.x.eq(self.y + y1),
                self.dac.eq(self.limit.y[-width:]),
        ]


class IOMux(Module, AutoCSR):
    def __init__(self, ins, outs):
        for i, o in zip(ins, outs):
            self.comb += i.demod.phase.eq(o.mod.phase)
        r = Array([i.y for i in ins] + [o.y for o in outs])
        for i, o in zip("abcdef", outs):
            m = CSRStorage(len(ins), reset=0, name="mux_%s" % i)
            setattr(self, "r_mux_%s" % i, m)
            self.comb += o.x.eq(optree("+", [Mux(m.storage[j], ini.y, 0)
                for j, ini in enumerate(ins)]))
            m = CSRStorage(log2_int(len(r), need_pow2=False),
                    reset=0, name="mux_relock_%s" % i)
            setattr(self, "r_mux_relock_%s" %i, m)
            self.sync += o.relock.x.eq(r[m.storage])


class Pid(Module, AutoCSR):
    def __init__(self):
        self.r_version = CSRStatus(8)
        self.r_version.status.reset = 1

        self.submodules.in_a = InChain(14)
        self.submodules.in_b = InChain(14)
        self.submodules.out_a = OutChain(14)
        self.submodules.out_b = OutChain(14)
        self.submodules.iomux = IOMux([self.in_a, self.in_b],
                [self.out_a, self.out_b])

