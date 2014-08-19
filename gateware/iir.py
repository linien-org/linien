from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus

from .filter import Filter


class Iir(Filter):
    def __init__(self, order=1, mode="pipelined",
            signal_width=25, coeff_width=18,
            wait=1, shift=16, intermediate_width=None):
        Filter.__init__(self, signal_width)
        assert mode in ("pipelined", "iterative")
        if intermediate_width is None:
            intermediate_width = signal_width + coeff_width

        self.r_z0 = CSRStorage(signal_width)
        self.r_shift = CSRStatus(8)
        self.r_shift.status.reset = shift

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
        self.sync += z.eq(Cat(Replicate(0, shift), self.r_z0.storage,
            Replicate(self.r_z0.storage[-1], intermediate_width-signal_width-shift)))
        zr, z = z, Signal.like(z, name="z0")
        self.sync += z.eq(zr)

        y = Signal.like(self.y)
        x = Signal.like(self.x)
        y_next = Signal.like(z)
        y_over = y_next[shift+signal_width-1:]
        y_pat = Signal.like(y_over, reset=-1)
        railed = Signal()
        self.comb += [
                railed.eq(~((y_over == y_pat) | (y_over == ~y_pat))),
                self.y.eq(y)
        ]
        self.sync += [
                If(self.mode[2],
                    x.eq(0)
                ).Elif(~self.mode[0],
                    x.eq(self.x)
                ),
                If(self.mode[3],
                    y.eq(0)
                ).Elif(~self.mode[1] & ~railed,
                    y.eq(y_next[shift:])
                )
        ]
        self.sync += self.mode_out.eq(self.mode)

        if mode == "pipelined":
            self.latency = (order + 1)*wait
            self.interval = 1
            r = [("b%i" % i, x, 0, False) for i in reversed(range(order + 1))]
            r += [("a%i" % i, y, 1, True) for i in reversed(range(1, order + 1))]
            for coeff, signal, side, invert in r:
                z0, z = z, Signal.like(z, name="z_" + coeff)
                self.comb += z.eq(z0 + signal*c[coeff])
                z_next = z
                for i in range(wait):
                    z0, z = z, Signal.like(z, name="zr%i_%s" % (i, coeff))
                    self.sync += z.eq(z0)
            self.comb += y_next.eq(z_next)

        elif mode == "iterative":
            self.latency = (2*order+1)*wait
            self.interval = self.latency
            ma = Signal((signal_width, True))
            mb = Signal((coeff_width, True))
            mc = Signal((intermediate_width, True))
            mp = Signal((intermediate_width, True))
            self.comb += mp.eq(ma*mb + mc)

            xx = [x] + [Signal((signal_width, True)) for i in range(order)]
            yy = [y] + [Signal((signal_width, True)) for i in range(order-1)]
            muls = []
            muls += [[b[i], xx[i], mp] for i in range(order+1)]
            muls += [[a[i], yy[i], mp] for i in range(order)]
            muls[-1][-1] = 0 # start with 0 for accu

            in_act = {}
            for i, (na, nb, nc) in enumerate(muls[::-1]):
                in_act[i] = [Cat(ma, mb, mc).eq(Cat(na, nb, nc))]
            in_act[0] += [
                    yn.eq(mp >> a0_shift),
                    ]
            in_act[len(in_act)-1] += [
                    Cat(*xx[1:]).eq(Cat(*xx[:-1])),
                    (Cat(*yy[1:]).eq(Cat(*yy[:-1])) if order > 1 else []),
                    ]
            state = Signal(max=len(in_act))
            t = Signal(max=wait)
            self.sync += [
                    t.eq(t + 1),
                    If(t == 0,
                        Case(state, in_act),
                    ),
                    If(t == wait-1,
                        t.eq(0),
                        If(state == len(in_act)-1,
                            state.eq(0),
                        ).Else(
                            state.eq(state + 1),
                        ),
                    ),
                    If(self.stop,
                        t.eq(0),
                        state.eq(0),
                        Cat(*xx[1:]).eq(0),
                        Cat(yn, *yy).eq(0),
                    )]
