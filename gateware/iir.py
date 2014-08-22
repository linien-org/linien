from migen.fhdl.std import *
from migen.genlib.misc import timeline
from migen.bank.description import CSRStorage, CSRStatus

from .filter import Filter


class Iir(Filter):
    def __init__(self, order=1, mode="pipelined",
            width=25, coeff_width=18,
            wait=1, shift=16, intermediate_width=None):
        Filter.__init__(self, width)
        assert mode in ("pipelined", "iterative")
        if intermediate_width is None:
            intermediate_width = width + coeff_width

        self.r_z0 = CSRStorage(width, reset=0)
        self.r_shift = CSRStatus(8, reset=shift)

        self.c = c = {}
        for i in "ab":
            for j in range(order + 1):
                name = "%s%i" % (i, j)
                if name == "a0":
                    continue
                ci = Signal((coeff_width, True), name=name)
                rci = CSRStorage(flen(ci), name=name)
                self.sync += ci.eq(rci.storage)
                c[name] = ci
                setattr(self, "r_" + name, rci)

        ###

        z = Signal((intermediate_width, True), name="z0r")
        self.sync += z[shift:].eq(Cat(self.r_z0.storage,
            Replicate(self.r_z0.storage[-1], intermediate_width-width-shift)))

        x = Signal.like(self.x)
        y = Signal.like(self.y)
        y_next = Signal.like(z)
        y_over = y_next[shift+width-1:]
        y_pat = Signal.like(y_over, reset=-1)
        railed = Signal()
        self.comb += [
                railed.eq(~((y_over == y_pat) | (y_over == ~y_pat))),
                self.error.eq(railed)
        ]
        self.sync += [
                If(self.clear,
                    self.y.eq(0),
                    y.eq(0),
                ).Elif(~railed,
                    self.y.eq(y_next[shift:]),
                    If(~self.hold,
                        y.eq(y_next[shift:])
                    )
                )
        ]
        r = [("b%i" % i, x) for i in reversed(range(order + 1))]
        r += [("a%i" % i, y) for i in reversed(range(1, order + 1))]

        if mode == "pipelined":
            self.comb += x.eq(self.x)
            self.latency = (order + 1)*wait
            self.interval = 1
            for coeff, signal in r:
                for i in range(wait):
                    z0, z = z, Signal.like(z, name="zr%i_%s" % (i, coeff))
                    self.sync += z.eq(z0)
                z0, z = z, Signal.like(z, name="z_" + coeff)
                self.comb += z.eq(z0 + signal*c[coeff])
            self.comb += y_next.eq(z)

        elif mode == "iterative":
            assert wait == 1
            self.latency = (2*order + 1)*wait
            self.interval = self.latency
            ma = Signal.like(self.y)
            mb = Signal.like(c["a1"])
            mm = Signal.like(z)
            mc = Signal.like(z)
            mp = Signal.like(z)
            self.sync += mm.eq(ma*mb), mp.eq(mm + mc), mc.eq(mp)
            steps = []
            for coeff, signal in r:
                steps.append([ma.eq(signal), mb.eq(c[coeff])])
            steps[1].append(mc.eq(z))
            steps[2].append(y_next.eq(mp))
            steps[-1].append(x.eq(self.x))
            self.sync += timeline(1, list(enumerate(steps)))
