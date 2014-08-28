# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *

from .filter import Filter
from .iir import Iir
from .limit import LimitCSR, Limit
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
        self.submodules.demod = Demodulate(width=width)

        self.r_tap = CSRStorage(3)

        self.errors = Signal(1)

        ###

        s = signal_width - width
        self.comb += [
                self.x.eq(self.adc << s),
                self.limit.x.eq(self.adc),
                self.iir_a.x.eq(self.limit.y << s),
                self.iir_b.x.eq(self.iir_a.y),
                self.demod.x.eq(Mux(self.r_tap.storage[0],
                    self.iir_b.y, self.iir_a.y) >> s),

                self.iir_a.hold.eq(self.hold),
                self.iir_b.hold.eq(self.hold),
                self.iir_a.clear.eq(self.clear),
                self.iir_b.clear.eq(self.clear),
                self.errors.eq(Cat(self.limit.error)),
        ]
        ys = Array([self.x, self.limit.y << s,
            self.iir_a.y, self.iir_b.y,
            self.demod.y << s, self.demod.y << s])
        self.sync += [
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

        self.submodules.relock = Relock(width=width + 1, shift=17)
        self.submodules.sweep = SweepCSR(width=width, shift=18)
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
        s = signal_width - width
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
                self.limit.x.eq((self.y >> s) + ya + self.relock.y),
                self.dac.eq(self.limit.y),
        ]
        self.sync += [
                self.iir_a.x.eq(self.x),
                self.iir_b.x.eq(self.iir_a.y),
                self.iir_c.x.eq(self.iir_b.y),
                self.iir_d.x.eq(self.iir_c.y),
                self.y.eq(ys[self.r_tap.storage]),
                ya.eq(self.mod.y + self.asg + self.sweep.y),
        ]


class IOMux(Module, AutoCSR):
    def __init__(self, ins, outs):
        csrs = []
        err = Cat([1] + [i.errors for i in ins] + [o.errors for o in outs])
        y = Array([i.y for i in ins] + [o.y for o in outs])
        for l, i, o in zip("abcdef", ins, outs):
            ric = CSRStorage(flen(err), name="in_%s_clear" % l)
            rih = CSRStorage(flen(err), name="in_%s_hold" % l)
            roc = CSRStorage(flen(err), name="out_%s_clear" % l)
            roh = CSRStorage(flen(err), name="out_%s_hold" % l)
            rr = CSRStorage(flen(err), name="out_%s_relock" % l)
            csrs += ric, rih, roc, roh, rr
            self.sync += [
                    i.hold.eq(err & rih.storage != 0),
                    i.clear.eq(err & ric.storage != 0),
                    o.hold.eq(err & roh.storage != 0),
                    o.clear.eq(err & roc.storage != 0),
                    o.relock.hold.eq(err & rr.storage != 0)
            ]
        for i, o in zip(ins, outs):
            self.comb += i.demod.phase.eq(o.mod.phase)
        for i, o in zip("abcdef", outs):
            m = CSRStorage(len(ins), name="out_%s_x" % i)
            f = CSRStorage(flen(o.x), name="out_%s_offset" % i)
            fr = Signal.like(o.x)
            self.comb += fr.eq(f.storage), o.x.eq(fr + optree("+", [
                Mux(m.storage[j], ini.y, 0) for j, ini in enumerate(ins)
                ])) # TODO: sat, const
            r = CSRStorage(log2_int(len(y), need_pow2=False),
                    name="out_%s_relock_x" % i)
            self.sync += o.relock.x.eq(y[r.storage] >> (signal_width - flen(o.relock.x)))
            csrs += m, f, r
        for csr in csrs:
            setattr(self, csr.name, csr)


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

