from migen.fhdl.std import *
from math import pi


class Iir(Module):
    def __init__(self, order=2, mode="pipelined", x=16, y=16,
            width=18, a0_shift=16, intermediate_width=48, wait=4):
        assert mode in ("pipelined", "iterative")

        if type(x) is type(0):
            x = Signal((x, True))
        if type(y) is type(0):
            y = Signal((y, True))
        self.x = x
        self.y = y
        x = Signal((width, True))
        y = Signal((width, True))
        self.bypass = Signal()
        
        self.comb += [
                x.eq(self.x << (width-flen(self.x))),
                self.y.eq(y >> (width-flen(self.y))),
                If(self.bypass, (
                    self.y.eq(self.x >> (flen(self.x)-flen(self.y)))
                        if flen(self.x) > flen(self.y) else
                    self.y.eq(self.x << (flen(self.y)-flen(self.x)))),
                )]

        b = [Signal((width, True), "b{}".format(i))
                for i in range(order+1)]
        a = [Signal((width, True), "a{}".format(i))
                for i in range(1, order+1)]
        self.coeffs = dict((s.backtrace[-1][0], s) for s in a+b)
        yn = Signal((width, True))
        self.a0_shift = a0_shift
        self.stop = Signal()

        if mode == "pipelined":
            self.latency = 1
            self.interval = 1
            ib = [Signal((intermediate_width, True), "ib{}".format(i))
                    for i in range(order+1)] + [0]
            ia = [Signal((intermediate_width, True), "ia{}".format(i))
                    for i in range(1, order+1)] + [ib[0]]
            self.sync += [ib[i].eq(b[i]*x + ib[i+1]) for i in range(order+1)]
            self.sync += [ia[i].eq(a[i]*y + ia[i+1]) for i in range(order)]
            self.comb += yn.eq(ia[0] >> a0_shift)
            self.sync += [
                    If(self.stop,
                        [iabi.eq(0) for iabi in ib[:-1] + ia[:-1]],
                    )]

        elif mode == "iterative":
            self.latency = (2*order+1)*wait
            self.interval = self.latency
            ma = Signal((width, True))
            mb = Signal((width, True))
            mc = Signal((intermediate_width, True))
            mp = Signal((intermediate_width, True))
            self.comb += mp.eq(ma*mb + mc)

            xx = [x] + [Signal((width, True)) for i in range(order)]
            yy = [y] + [Signal((width, True)) for i in range(order-1)]
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

        inc = Signal()
        dec = Signal()
        wound_up = Signal()
        self.hold = Signal()
        self.railed = Signal(2)
        yo = Signal((width, True))
        self.sync += yo.eq(y)
        self.comb += [
                inc.eq(yn > yo),
                dec.eq(yn < yo),
                wound_up.eq((self.railed[0] & inc) | (self.railed[1] & dec)),
                If(wound_up | self.hold,
                    y.eq(yo),
                ).Else(
                    y.eq(yn),
                )]


class TB(Module):
    def __init__(self, gen=[], params={}, **kwargs):
        self.submodules.iir = Iir(**kwargs)
        self.params = params
        self.gen = gen
        self.x = []
        self.y = []

    def do_simulation(self, s):
        if s.cycle_counter == 0:
            for k, v in self.params.items():
                p = self.iir.coeffs[k]
                vs = int(round(v*2**(self.iir.a0_shift)))
                vp = vs&((1<<flen(p))-1)
                print(k, v, vs, vp)
                s.wr(p, vp)
        else:
            for xi in self.gen:
                self.x.append(xi)
                xi *= 2**(flen(self.iir.x)-1)
                s.wr(self.iir.x, xi)
                yi = s.rd(self.iir.y)/2**(flen(self.iir.y)-1)
                self.y.append(yi)
                break


def get_params(typ="pi", ts=100e6, f0=1., k=1., g=1.):
    if typ == "pi":
        return {
                "a1": (1-pi*f0*ts/g)/(1+pi*f0*ts/g),
                "b0": k*(1+pi*f0*ts)/(1+pi*f0*ts/g),
                "b1": -k*(1-pi*f0*ts)/(1+pi*f0*ts/g),
                }



def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel
    from matplotlib import pyplot as plt
    import numpy as np

    iir = Iir(width=35, intermediate_width=70, a0_shift=26,
            order=2, mode="iterative")
    print(verilog.convert(iir, ios={iir.x, iir.y,
        iir.hold, iir.railed, iir.bypass, iir.stop} |
        set(iir.coeffs.values())))

    n = 10000
    x = np.zeros(n)
    x[:n/2] = 1e-3
    p = get_params("pi", f0=1e1, ts=1e3*10, k=1e-4, g=1e7)
    tb = TB(iter(x), p, width=35, intermediate_width=70,
            a0_shift=26, order=1, mode="iterative")
    #print(verilog.convert(tb))
    sim = Simulator(tb, TopLevel("iir.vcd"))
    sim.run(n)
    plt.plot(tb.x)
    plt.plot(tb.y)
    plt.show()


if __name__ == "__main__":
    main()

