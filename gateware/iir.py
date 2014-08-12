import math

from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR

from migen.fhdl.bitcontainer import bits_for
from migen.bus.csr import Initiator
from migen.bank.csrgen import get_offset, Bank
from migen.bus.transactions import TWrite


class Iir(Module, AutoCSR):
    def __init__(self, order=1, mode="pipelined",
            signal_width=18, coeff_width=25, intermediate_width=48,
            wait=4):
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
        rail = Signal()
        self.comb += [
                self.mode_out.eq((self.mode_in & ~self.r_mask.storage) |
                    self.r_cmd.storage | Cat(rail, 0, 0, 0)),
                self.r_mode.status.eq(self.mode_out),
                rail.eq(
                    (yn[-1] & (~yn[signal_width-1:-1] != 0)) |
                    (~yn[-1] & (yn[signal_width-1:-1] != 0))),
                If(rail,
                    self.y.eq(yo),
                ).Else(
                    self.y.eq(yn),
                )]

        if mode == "pipelined":
            self.latency = order + 1
            self.interval = 1
            stage = Signal((intermediate_width, True), name="i_0")
            self.sync += stage.eq(self.r_bias.storage << c["a0"])
            r = [("b%i" % i, self.x, 1) for i in reversed(range(order + 1))]
            r += [("a%i" % i, self.y, 0) for i in reversed(range(1, order + 1))]
            for coeff, sig, side in r:
                _stage = stage
                stage = Signal((intermediate_width, True), name="i_" + coeff)
                m = Mux(self.mode_out[side], 0, _stage)
                self.sync += [
                        If(self.mode_out[side + 2],
                            stage.eq(0)
                        ).Else(
                            stage.eq(c[coeff]*sig + m)
                        )
                ]
            self.comb += yn.eq(stage >> c["a0"])

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



class TB(Module):
    def __init__(self, gen=[], **kwargs):
        self.submodules.iir = Iir(**kwargs)
        self.desc = self.iir.get_csrs()
        self.submodules.bank = Bank(self.desc)
        self.submodules.init = Initiator(self.writes(),
                self.bank.bus)
        self.params = {}
        self.gen = iter(gen)
        self.x = []
        self.y = []

    def writes(self):
        for k in sorted(self.params):
            n = flen(self.iir.c[k])
            v = self.params[k] #& ((1<<n) - 1)
            print(k, hex(v))
            a = get_offset(self.desc, k)
            b = (n + 8 - 1)//8
            for i in reversed(range(b)):
                vi = (v >> (i*8)) & 0xff
                print(i, a, vi)
                yield TWrite(a, vi)
                a += 1

    def do_simulation(self, selfp):
        try:
            xi = next(self.gen)
        except StopIteration:
            raise StopSimulation
        self.x.append(xi)
        xi = xi*2**(flen(self.iir.x)-1)
        selfp.iir.x = xi
        yi = selfp.iir.y
        yi = yi/2**(flen(self.iir.y)-1)
        self.y.append(yi)


def get_params(typ="pi", f=1., k=1., g=1., shift=None, width=25, fs=1.):
    f *= math.pi/fs
    if typ == "pi":
        p = {
                "a1":  (1 - f/g)/(1 + f/g),
                "b0":  k*(1 + f)/(1 + f/g),
                "b1": -k*(1 - f)/(1 + f/g),
        }
    if shift is None:
        shift = width - 1 - max(math.ceil(math.log2(abs(p[k]))) for k in p)
    for k in p:
        p[k] = int(p[k]*2**shift)
        n = bits_for(p[k], True)
        assert n <= width, (k, hex(p[k]), n, width)
    p["a0"] = shift
    return p



def main():
    from migen.fhdl import verilog
    from migen.sim.generic import run_simulation
    from matplotlib import pyplot as plt
    import numpy as np

    iir = Iir()
    print(verilog.convert(iir, ios={iir.x, iir.y,
        iir.mode_in, iir.mode_out}))

    n = 10000
    x = np.zeros(n)
    x[n/4:n/2] = .5
    x[n/2:3*n/4] = -x[n/4:n/2]
    tb = TB(x, order=1, mode="pipelined")
    tb.params = get_params("pi", f=4e-6, k=1., g=1e90,
            width=flen(tb.iir.c["a1"]))
    #print(verilog.convert(tb))
    run_simulation(tb, vcd_name="iir.vcd")
    plt.plot(tb.x)
    plt.plot(tb.y)
    plt.show()


if __name__ == "__main__":
    main()

