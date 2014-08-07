from migen.fhdl.std import *
from migen.bank.description import CSRStorage, AutoCSR

from cordic import Cordic
from iir import Iir


class Lockin(Module, AutoCSR):
    def __init__(self, width=16):
        self.submodules.iir_pre = Iir(x=width, y=width, width=35,
                intermediate_width=70, order=2, mode="iterative")
        self.submodules.iir_post = Iir(x=width, y=width, width=35,
                intermediate_width=70, order=2, mode="iterative")

        self.submodules.cordic_lo = Cordic(width=width,
                eval_mode="pipelined", cordic_mode="rotate",
                func_mode="circular")
        self.submodules.cordic_sig = Cordic(width=width,
                eval_mode="pipelined", cordic_mode="rotate",
                func_mode="circular")

        self.cordic_lo.xi.reset = int(round(
            2**(width-2)/self.cordic_lo.gain))
        self.cordic_sig.xi.reset = self.cordic_lo.xi.reset
        self.x = Signal((width, True))
        self.y = Signal((width, True))
        self.lo = Signal((width, True))
        self.frequency = Signal(width)
        p1 = Signal(width)
        p2 = Signal(width)
        self.phase = Signal(width)
        self.sync += p1.eq(p1 + self.frequency)
        self.comb += [
                self.iir_pre.x.eq(self.x),
                p2.eq(p1 + self.phase),
                self.cordic_sig.zi.eq(p2),
                #self.cordic_sig.xi.eq(self.x>>1), # cheap gain compensation
                #self.iir_post.x.eq(self.cordic_sig.xo),
                self.iir_post.x.eq(self.cordic_sig.xo*self.x),
                self.y.eq(self.iir_post.y),
                self.cordic_lo.zi.eq(p1),
                self.lo.eq(self.cordic_lo.xo),
                ]

        for i, iir in enumerate((self.iir_pre, self.iir_post)):
            for n, c in iir.coeffs.items():
                csr = CSRStorage(flen(c), name="iir{}_{}".format(i, n))
                setattr(self, "_iir{}_{}".format(i, n), csr)
                self.comb += c.eq(csr.storage)
        for reg, name in [
                (self.frequency, "frequency"),
                (self.phase, "phase"), 
                ]:
            csr = CSRStorage(flen(reg), name=name)
            setattr(self, "_{}".format(name), csr)
            self.comb += reg.eq(csr.storage)
        self._bypass = CSRStorage(6)
        self.comb += Cat(self.iir_pre.bypass, self.iir_pre.stop,
                self.iir_pre.hold, self.iir_post.bypass,
                self.iir_post.stop, self.iir_post.hold).eq(
                        self._bypass.storage)


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.lockin = Lockin(**kwargs)

    def do_simulation(self, s):
        pass


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel

    s = Lockin()
    print(verilog.convert(s, ios=set()))

    n = 200
    tb = TB()
    sim = Simulator(tb, TopLevel("lockin.vcd"))
    sim.run(n+20)


if __name__ == "__main__":
    main()
