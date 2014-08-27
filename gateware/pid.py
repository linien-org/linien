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
        self.submodules.limit = LimitCSR(width=width)
        self.submodules.iir_a = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.iir_b = Iir(width=signal_width,
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
        self.submodules.demod = Demodulate(width=signal_width)

        self.r_tap = CSRStorage(3)

        self.errors = Signal(1)

        ###

        self.comb += [
                self.x.eq(self.adc << (signal_width - width)),
                self.limit.x.eq(self.adc),
                self.iir_a.x.eq(self.limit.y << (signal_width - width)),
                self.iir_b.x.eq(self.iir_a.y),
                self.demod.x.eq(Mux(self.r_tap.storage[0],
                    self.iir_b.y, self.iir_a.y)),

                self.iir_a.hold.eq(self.hold),
                self.iir_b.hold.eq(self.hold),
                self.iir_a.clear.eq(self.clear),
                self.iir_b.clear.eq(self.clear),
                self.errors.eq(Cat(self.limit.error))
        ]
        ys = Array([self.x, self.limit.y << (signal_width - width),
            self.iir_a.y, self.iir_b.y, self.demod.y, self.demod.y])
        self.sync += [
                self.error.eq(self.limit.error),
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
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
        self.submodules.iir_d = Iir(width=signal_width,
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
#        self.submodules.iir_d = Iir(width=signal_width,
#                coeff_width=coeff_width, order=2)

        self.submodules.relock = Relock(width=width + 1, shift=18)
        self.submodules.sweep = SweepCSR(width=width, shift=19)
        self.submodules.mod = Modulate(width=width)
        self.asg = Signal((width, True))
        self.submodules.limit = LimitCSR(width=width, guard=3)
        self.dac = Signal((width, True))

        self.r_tap = CSRStorage(3)

        self.errors = Signal(2)
        # self.relock.hold, self.clear, self.hold <= digital mux

        ya = Signal((width + 2, True))
        ys = Array([self.x, self.iir_a.y, self.iir_b.y,
            self.iir_c.y, self.iir_d.y])
        self.comb += [
                self.errors.eq(Cat(self.relock.error, self.limit.error)),

                self.iir_a.clear.eq(self.clear),
                self.iir_b.clear.eq(self.clear),
                self.iir_c.clear.eq(self.clear),
                self.iir_d.clear.eq(self.clear),
                #self.sweep.clear.eq(self.clear), # end sweep
                self.relock.clear.eq(self.limit.error), # turn

                self.iir_a.hold.eq(self.hold),
                self.iir_b.hold.eq(self.hold),
                self.iir_c.hold.eq(self.hold),
                self.iir_d.hold.eq(self.hold),
                #self.sweep.hold.eq(self.hold), # pause sweep
                #self.relock.hold.eq(self.hold), # digital trigger
        ]
        self.sync += [
                self.iir_a.x.eq(self.x),
                self.iir_b.x.eq(self.iir_a.y),
                self.iir_c.x.eq(self.iir_b.y),
                self.iir_d.x.eq(self.iir_c.y),
                self.y.eq(ys[self.r_tap.storage]),
                ya.eq((self.sweep.y + self.mod.y) + self.asg),
                self.limit.x.eq((self.y >> (signal_width - width))
                    + self.relock.y + ya),
                self.dac.eq(self.limit.y),
        ]


class IOMux(Module, AutoCSR):
    def __init__(self, ins, outs):
        err = Cat([1] + [i.errors for i in ins] + [o.errors for o in outs])
        for l, i, o in zip("abcdef", ins, outs):
            ri = CSRStorage(2*flen(err), name="mux_in_state")
            setattr(self, "r_mux_in_state_%s" % l, ri)
            ro = CSRStorage(2*flen(err), name="mux_out_state")
            setattr(self, "r_mux_out_state_%s" % l, ro)
            rr = CSRStorage(2*flen(err), name="mux_out_relock")
            setattr(self, "r_mux_out_relock_%s" % l, rr)
            self.sync += [
                    i.hold.eq(err & ri.storage[:flen(err)] != 0),
                    i.clear.eq(err & ri.storage[flen(err):] != 0),
                    o.hold.eq(err & ro.storage[:flen(err)] != 0),
                    o.clear.eq(err & ro.storage[flen(err):] != 0)
                    o.relock.hold.eq(err & rr.storage[:flen(err)] != 0)
                    o.sweep.clear.eq(err & rr.storage[flen(err):] != 0)
            ]
        for i, o in zip(ins, outs):
            self.comb += i.demod.phase.eq(o.mod.phase)
        y = Array([i.y for i in ins] + [o.y for o in outs])
        for i, o in zip("abcdef", outs):
            m = CSRStorage(len(ins), reset=0, name="mux_%s" % i)
            setattr(self, "r_mux_%s" % i, m)
            self.comb += o.x.eq(optree("+", [Mux(m.storage[j], ini.y, 0)
                for j, ini in enumerate(ins)]))
            m = CSRStorage(log2_int(len(y), need_pow2=False),
                    reset=0, name="mux_relock_%s" % i)
            setattr(self, "r_mux_relock_%s" %i, m)
            self.sync += o.relock.x.eq(y[m.storage] >> (signal_width - flen(o.dac)))


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

