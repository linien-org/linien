import math

from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR

from migen.fhdl.bitcontainer import bits_for
from migen.bus.csr import Initiator
from migen.bank.csrgen import get_offset, Bank
from migen.bus.transactions import TWrite


class Iir(Module, AutoCSR):
    def __init__(self, order=2, mode="pipelined",
            signal_width=25, coeff_width=18, intermediate_width=48,
            wait=4):
        assert mode in ("pipelined", "iterative")

        self.x = Signal((signal_width, True))
        self.y = Signal((signal_width, True))
        self.mode_in = Signal(2) # hold, clear
        self.mode_out = Signal(2)

        self.r_cmd = CSRStorage(2)
        self.r_mask = CSRStorage(2)
        self.r_mode = CSRStatus(2)
        self.r_bias = CSRStorage(intermediate_width)

        self.c = c = {}
        for i in "ab":
            for j in range(order + 1):
                name = "%s%i" % (i, j)
                if name == "a0":
                    ci = Signal(max=intermediate_width)
                else:
                    ci = Signal((coeff_width, True))
                rci = CSRStorage(flen(ci), name=name)
                self.comb += ci.eq(rci.storage)
                c[name] = ci
                setattr(self, "r_" + name, rci)

        ###

        yn = Signal((signal_width + 1, True))
        yo = Signal((signal_width, True))
        self.sync += yo.eq(self.y)
        rail = Signal()
        mode = Signal(2)
        self.comb += [
                self.mode_out.eq((self.mode_in & ~self.r_mask.storage) |
                    self.r_cmd.storage | Cat(rail, 0)),
                self.r_mode.status.eq(self.mode_out),
                rail.eq(yn[-2] != yn[-1]),
                If(rail,
                    self.y.eq(yo),
                ).Else(
                    self.y.eq(yn),
                )]

        if mode == "pipelined":
            self.latency = 2
            self.interval = 1
            stage = Signal((intermediate_width, True))
            self.sync += stage.eq(self.r_bias.storage)
            stages = [stage]
            r = [("b%i" % i, self.x) for i in reversed(range(order + 1))]
            r += [("a%i" % i, self.y) for i in reversed(range(1, order + 1))]
            for i, (coeff, sig) in enumerate(r):
                stage, _stage = Signal.like(stage), stage
                stages.append(stage)
                self.sync += If(~self.mode_out[0], stage.eq(c[coeff]*sig + _stage))
            self.comb += yn.eq(stage >> c["a0"])
            self.sync += If(self.mode_out[1], [i.eq(0) for i in stages])

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
    def __init__(self, gen=[], params={}, **kwargs):
        self.submodules.iir = Iir(**kwargs)
        self.desc = self.iir.get_csrs()
        self.submodules.bank = Bank(self.desc)
        self.submodules.init = Initiator(self.writes(params),
                self.bank.bus)
        self.gen = iter(gen)
        self.x = []
        self.y = []

    def writes(self, params):
        for k in sorted(params):
            n = flen(self.iir.c[k])
            v = params[k]
            print(k, v, hex(v))
            for i in range(0, n, 8):
                adr = get_offset(self.desc, k) + (n - i + 8 - 1)//8 - 1
                yield TWrite(adr, (v >> i) & 0xff)

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
                "a1": (1 - f/g)/(1 + f/g),
                "b0": k*(1 + f)/(1 + f/g),
                "b1": -k*(1 - f)/(1 + f/g),
                }
    if shift is None:
        shift = width + 1 - max(bits_for(v, require_sign_bit=True)
                for v in p.values())
    for k in p:
        p[k] = int(p[k]*2**shift)
    p["a0"] = shift
    return p



def main():
    from migen.fhdl import verilog
    from migen.sim.generic import run_simulation
    from matplotlib import pyplot as plt
    import numpy as np

    #iir = Iir()
    #print(verilog.convert(iir, ios={iir.x, iir.y,
    #    iir.mode_in, iir.mode_out}))

    n = 1000
    x = np.zeros(n)
    x[100:n/2] = 1e-3
    p = get_params("pi", f=1e-3, k=1e-2, g=1e9)
    tb = TB(x, p, order=1, mode="pipelined")
    #print(verilog.convert(tb))
    run_simulation(tb, vcd_name="iir.vcd")
    plt.plot(tb.x)
    plt.plot(tb.y)
    plt.show()


if __name__ == "__main__":
    main()

