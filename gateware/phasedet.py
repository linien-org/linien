from migen.fhdl.std import *
from migen.bank.description import CSRStorage, AutoCSR

from iir import Iir


class Phasedet(Module, AutoCSR):
    def __init__(self, width=16):
        self.submodules.iir = Iir(order=2, x=16, y=16, width=18,
                intermediate_width=48, mode="iterative")
        self.x = Signal((width, True))
        x0 = Signal((width, True))
        self.frequency = Signal(width)
        self.phase = Signal(width)
        p = Signal(width)
        self.y = Signal((width, True))
        self.sync += [
                If(x0[-1] & ~self.x[-1], # riging edge
                    self.iir.x.eq(p + self.phase),
                ),
                p.eq(p + self.frequency),
                x0.eq(self.x),
                self.y.eq(self.iir.y),
                ]

        for n, c in self.iir.coeffs.items():
            csr = CSRStorage(flen(c), name="iir_{}".format(n))
            setattr(self, "_iir_{}".format(n), csr)
            self.comb += c.eq(csr.storage)
        for reg, name in [
                (self.frequency, "frequency"),
                (self.phase, "phase"),
                ]:
            csr = CSRStorage(flen(reg), name=name)
            setattr(self, "_{}".format(name), csr)
            self.comb += reg.eq(csr.storage)
        self._bypass = CSRStorage(6)
        self.comb += Cat(self.iir.bypass, self.iir.stop,
                self.iir.hold).eq(self._bypass.storage)


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.phasedet = Phasedet(**kwargs)

    def do_simulation(self, s):
        pass


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel

    s = Phasedet()
    print(verilog.convert(s, ios=set()))

    n = 200
    tb = TB()
    sim = Simulator(tb, TopLevel("phasedet.vcd"))
    sim.run(n+20)


if __name__ == "__main__":
    main()
