from migen.fhdl.std import *
from migen.bank.description import CSRStorage

from .filter import Filter


class Iir(Filter):
    def __init__(self, order=1, mode="pipelined",
            signal_width=24, coeff_width=18, intermediate_width=None,
            wait=1):
        Filter.__init__(self, signal_width)
        assert mode in ("pipelined", "iterative")
        if intermediate_width is None:
            intermediate_width = signal_width + coeff_width

        self.r_z0 = CSRStorage(signal_width)

        self.c = c = {}
        for i in "ab":
            for j in range(order + 1):
                name = "%s%i" % (i, j)
                if name == "a0":
                    ci = Signal(max=intermediate_width, name=name)
                else:
                    ci = Signal((coeff_width, True), name=name)
                rci = CSRStorage(flen(ci), name=name)
                self.sync += ci.eq(rci.storage)
                c[name] = ci
                setattr(self, "r_" + name, rci)

        ###

        y_last = Signal.like(self.y)
        self.sync += y_last.eq(self.y)
        railed = Signal()
        y_next = Signal((intermediate_width, True))
        self.comb += [
                railed.eq(Replicate(y_next[signal_width-1:-1], 1) !=
                    Replicate(y_next[-1], intermediate_width - signal_width)),
                If(railed,
                    self.y.eq(y_last),
                ).Else(
                    self.y.eq(y_next),
                ),
        ]
        self.sync += self.mode_out.eq(self.mode)

        z = Signal((intermediate_width, True), name="z")
        self.sync += z.eq(self.r_z0.storage << c["a0"])

        if mode == "pipelined":
            self.latency = (order + 1)*wait
            self.interval = 1
            r = [("b%i" % i, self.x, 0, False) for i in reversed(range(order + 1))]
            r += [("a%i" % i, self.y, 1, True) for i in reversed(range(1, order + 1))]
            for coeff, signal, side, invert in r:
                z0, z = z, Signal((intermediate_width, True), name="z_" + coeff)
                self.sync += [
                        If(self.mode[side + 2],
                            z.eq(0)
                        ).Elif(~self.mode[side],
                            z.eq(z0 + signal*c[coeff])
                        )
                ]
                for i in range(wait - 1):
                    z0, z = z, Signal((intermediate_width, True),
                            name="zr%i_%s" % (i, coeff))
                    self.sync += z.eq(z0)
            self.comb += y_next.eq(z >> c["a0"])

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
