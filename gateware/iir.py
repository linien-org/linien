from migen.fhdl.std import *
from migen.genlib.misc import timeline
from migen.bank.description import CSRStorage, CSRStatus

from .filter import Filter


class Iir(Filter):
    def __init__(self, order=1, mode="pipelined",
            width=25, coeff_width=18,
            shift=16, intermediate_width=None):
        Filter.__init__(self, width)
        assert mode in ("pipelined", "iterative")
        if intermediate_width is None:
            intermediate_width = width + coeff_width + bits_for(2*(order + 1))

        self.r_z0 = CSRStorage(width, reset=0)
        self.r_shift = CSRStatus(bits_for(shift), reset=shift)
        self.r_width = CSRStatus(bits_for(shift), reset=coeff_width)
        self.r_interval = CSRStatus(8)

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
        z0 = Signal((width, True))
        self.comb += z0.eq(self.r_z0.storage)
        self.sync += z.eq(z0 << shift)

        y_lim = Signal.like(self.y)
        y_next = Signal.like(z)
        y_over = y_next[shift+width-1:]
        y_pat = Signal.like(y_over, reset=-1)
        y = Signal.like(self.y)
        railed = Signal()
        self.comb += [
                railed.eq(~((y_over == y_pat) | (y_over == ~y_pat))),
                If(railed,
                    y_lim.eq(self.y)
                ).Else(
                    y_lim.eq(y_next[shift:])
                )
        ]
        self.sync += [
                self.error.eq(railed),
                self.y.eq(y_lim),
                If(self.clear,
                    y.eq(0)
                ).Elif(~self.hold,
                    y.eq(y_lim)
                )
        ]

        if mode == "pipelined":
            r = [("b%i" % i, self.x) for i in reversed(range(order + 1))]
            r += [("a%i" % i, y) for i in reversed(range(1, order + 1))]
            for coeff, signal in r:
                zr = Signal.like(z)
                self.sync += zr.eq(z)
                z = Signal.like(zr)
                self.comb += z.eq(zr + signal*c[coeff])
            self.comb += y_next.eq(z)
            self.latency = order + 1
            self.interval = 1

        elif mode == "iterative":
            ma = Signal.like(self.y)
            mb = Signal.like(c["a1"])
            mm = Signal.like(z)
            mc = Signal.like(z)
            mp = Signal.like(z)
            self.sync += mm.eq(ma*mb), mc.eq(mp)
            self.comb += mp.eq(mm + mc)
            steps = []
            x = [self.x] + [Signal.like(self.x) for i in range(order + 1)]
            for i in reversed(range(order + 1)):
                steps.append([x[i + 1].eq(x[i]), ma.eq(x[i]), mb.eq(c["b%i" % i])])
            y = [None, y] + [Signal.like(y) for i in range(1, order + 1)]
            for i in reversed(range(1, order + 1)):
                steps.append([y[i + 1].eq(y[i]), ma.eq(y[i]), mb.eq(c["a%i" % i])])
            steps[1].append(mc.eq(z))
            self.latency = order + 4
            if order == 1:
                steps.append([])
                self.latency += 1
            steps[int(order > 1)].append(y_next.eq(mp))
            self.sync += timeline(1, list(enumerate(steps)))
            self.interval = len(steps)

        else:
            raise ValueError

        self.r_interval.status.reset = self.interval
