from migen.fhdl.std import *
from migen.bank.description import CSRStorage
from migen.genlib.cordic import Cordic

from .filter import Filter


class Demodulate(Filter):
    def __init__(self, freq_width=32, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        self.r_phase = CSRStorage(width)
        self.phase = Signal(width)

        self.submodules.cordic = Cordic(width=width,
                eval_mode="pipelined", cordic_mode="rotate",
                func_mode="circular")
        self.comb += [
                self.cordic.xi.eq(self.x),
                self.cordic.zi.eq(self.phase + self.r_phase.storage),
                self.y.eq(self.cordic.xo),
        ]


class Modulate(Filter):
    def __init__(self, freq_width=32, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        self.r_freq = CSRStorage(freq_width)
        self.r_amp = CSRStorage(width)
        self.phase = Signal(freq_width)

        z = Signal(freq_width)
        self.sync += z.eq(z + self.r_freq.storage)

        self.submodules.cordic = Cordic(width=width,
                eval_mode="pipelined", cordic_mode="rotate",
                func_mode="circular")
        self.comb += [
                self.phase.eq(z[freq_width-width:]),
                self.cordic.xi.eq(self.r_amp.storage + self.x),
                self.y.eq(self.cordic.xo),
        ]


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
