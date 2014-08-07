from migen.fhdl.std import *


class Limit(Module):
    def __init__(self, width=16):
        self.minval = Signal((width, True))
        self.maxval = Signal((width, True))
        self.x = Signal((width, True))
        self.y = Signal((width, True))
        self.railed = Signal(2)
        self.comb += [
                If(self.x >= self.maxval,
                    self.y.eq(self.maxval),
                    self.railed.eq(0b01),
                ).Elif(self.x <= self.minval,
                    self.y.eq(self.minval),
                    self.railed.eq(0b10),
                ).Else(
                    self.y.eq(self.x),
                    self.railed.eq(0b00),
                )]


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.limit = Limit(**kwargs)
        self.x = []
        self.y = []

    def do_simulation(self, s):
        if s.cycle_counter == 0:
            s.wr(self.limit.maxval, 1<<10)
            s.wr(self.limit.minval, 0xffff&(-(1<<10)))
        s.wr(self.limit.x, s.cycle_counter << 6)
        self.x.append(s.rd(self.limit.x))
        self.y.append(s.rd(self.limit.y))


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel
    import matplotlib.pyplot as plt

    s = Limit()
    print(verilog.convert(s, ios=set()))

    n = 1<<10
    tb = TB()
    sim = Simulator(tb, TopLevel("limit.vcd"))
    sim.run(n)
    plt.plot(tb.x)
    plt.plot(tb.y)
    plt.show()


if __name__ == "__main__":
    main()
