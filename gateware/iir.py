from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR


class Iir(Module, AutoCSR):
    def __init__(self, order=1, mode="pipelined",
            signal_width=25, coeff_width=18, intermediate_width=48,
            wait=1):
        assert mode in ("pipelined", "iterative")

        self.x = Signal((signal_width, True))
        self.y = Signal((signal_width, True))
        self.mode_in = Signal(4) # holda, holdb, cleara, clearb
        self.mode_out = Signal(4)

        self.r_cmd = CSRStorage(4)
        self.r_mask = CSRStorage(4)
        self.r_mode = CSRStatus(4)
        self.r_bias = CSRStorage(signal_width)

        self.c = c = {}
        for i in "ab":
            for j in range(order + 1):
                name = "%s%i" % (i, j)
                if name == "a0":
                    ci = Signal(max=intermediate_width, name=name)
                else:
                    ci = Signal((coeff_width, True), name=name)
                rci = CSRStorage(flen(ci), name=name)
                self.comb += ci.eq(rci.storage)
                c[name] = ci
                setattr(self, "r_" + name, rci)

        ###

        yn = Signal((intermediate_width, True))
        yo = Signal((signal_width, True))
        self.sync += yo.eq(self.y)
        railed = Signal()
        mode_in = Signal.like(self.mode_out)
        mode = Signal.like(self.mode_out)
        #limit = (1<<(signal_width - 1)) - 1
        self.comb += [
                railed.eq(
                    (yn[-1] & (~yn[signal_width - 1:-1] != 0)) |
                    (~yn[-1] & (yn[signal_width - 1:-1] != 0))),
                    #(yn < -limit) | (yn >= limit)),
                If(railed,
                    self.y.eq(yo),
                ).Else(
                    self.y.eq(yn),
                ),
                mode.eq(mode_in | Cat(railed, 0, 0, 0)),
                self.r_mode.status.eq(self.mode_out)
        ]
        self.sync += [
                mode_in.eq((self.mode_in & ~self.r_mask.storage) |
                    self.r_cmd.storage),
                self.mode_out.eq(mode)
        ]

        z = Signal((intermediate_width, True), name="z_bias")
        self.sync += z.eq(self.r_bias.storage << c["a0"])
        
        if mode == "pipelined":
            self.latency = (order + 1)*wait
            self.interval = 1
            r = [("b%i" % i, self.x, 1) for i in reversed(range(order + 1))]
            r += [("a%i" % i, -self.y, 0) for i in reversed(range(1, order + 1))]
            for coeff, sig, side in r:
                z0, z = z, Signal((intermediate_width, True), name="z_" + coeff)
                self.sync += [
                        If(mode[side + 2],
                            z.eq(0)
                        ).Else(
                            z.eq(c[coeff]*sig + Mux(mode[side], 0, z0))
                        )
                ]
                for i in range(wait - 1):
                    z0, z = z, Signal((intermediate_width, True), name="zr%i_%s" %
                            (i, coeff))
                    self.sync += z.eq(z0)
            self.comb += yn.eq(z >> c["a0"])

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
