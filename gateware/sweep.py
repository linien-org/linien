from migen.fhdl.std import *


class Sweep(Module):
    def __init__(self, width=16, step_width=32):
        guard = step_width - width

        self.stop = Signal()
        self.step = Signal((step_width, True))
        self.maxval = Signal((width, True))
        self.minval = Signal((width, True))

        self.y = Signal((width, True))
        y = Signal((step_width, True))
        yn = Signal((step_width, True))
        direction = Signal()
        self.comb += [
                self.y.eq(y >> guard),
                If(direction,
                    yn.eq(y + self.step),
                ).Else(
                    yn.eq(y - self.step),
                )]
        self.sync += [
                If((yn >> guard) >= self.maxval,
                    direction.eq(0),
                    y.eq(self.maxval << guard),
                ).Elif((yn >> guard) <= self.minval,
                    direction.eq(1),
                    y.eq(self.minval << guard),
                ).Else(
                    y.eq(yn),
                ),
                If(self.stop,
                    y.eq(0),
                    direction.eq(0),
                )]


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.sweep = Sweep(**kwargs)
        self.out = []

    def do_simulation(self, s):
        if s.cycle_counter == 0:
            s.wr(self.sweep.step, 1<<20)
            s.wr(self.sweep.maxval, 1<<10)
            s.wr(self.sweep.minval, 0xffff&(-(1<<10)))
        self.out.append(s.rd(self.sweep.y))


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel
    import matplotlib.pyplot as plt

    s = Sweep()
    print(verilog.convert(s, ios=set()))

    n = 200
    tb = TB()
    sim = Simulator(tb, TopLevel("sweep.vcd"))
    sim.run(n)
    plt.plot(tb.out)
    plt.show()



if __name__ == "__main__":
    main()
