from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus
from migen.genlib.cordic import Cordic

from .filter import Filter


class Demodulate(Filter):
    def __init__(self, freq_width=32, **kwargs):
        Filter.__init__(self, **kwargs)
        return


class Modulate(Filter):
    def __init__(self, freq_width=32, **kwargs):
        Filter.__init__(self, **kwargs)
        return


        self.submodules.cordic = Cordic(width=width,
                eval_mode="pipelined", cordic_mode="rotate",
                func_mode="circular")
        self.cordic.xi.reset = int(2**(width-1)/self.cordic.gain-1)
        self.frequency = Signal(width)
        self.y = Signal((width, True))
        p = Signal(width)
        self.sync += p.eq(p + self.frequency)
        self.comb += [
                self.cordic.zi.eq(p),
                self.y.eq(self.cordic.xo),
                ]

        for reg, name in [
                (self.frequency, "frequency"),
                ]:
            csr = CSRStorage(flen(reg), name=name)
            setattr(self, "_{}".format(name), csr)
            self.comb += reg.eq(csr.storage)


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.modulate = Modulate(**kwargs)
        self.out = []

    def do_simulation(self, s):
        if s.cycle_counter == 0:
            s.wr(self.modulate.frequency, 345)
        self.out.append(s.rd(self.modulate.y))


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel
    import matplotlib.pyplot as plt

    s = Modulate()
    print(verilog.convert(s, ios=set()))

    n = 2000
    tb = TB()
    sim = Simulator(tb, TopLevel("modulate.vcd"))
    sim.run(n+20)
    plt.plot(tb.out)
    plt.show()



if __name__ == "__main__":
    main()
