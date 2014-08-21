from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus

from .filter import Filter
from .limit import LimitCSR


class Sweep(Module):
    def __init__(self, width):
        self.run = Signal()
        self.step = Signal(width - 1)
        self.turn = Signal()
        self.hold = Signal()
        self.y = Signal((width, True))

        ###

        yn = Signal((width + 1, True))
        up = Signal()
        zero = Signal()

        self.comb += [
                If(zero,
                    yn.eq(0)
                ).Elif(self.hold,
                    yn.eq(self.y),
                ).Elif(up,
                    yn.eq(self.y + self.step),
                ).Else(
                    yn.eq(self.y - self.step),
                )
        ]
        self.sync += [
                self.y.eq(yn),
                zero.eq(0),
                If(self.run,
                    If(self.turn,
                        up.eq(~up)
                    )
                ).Elif(yn < 0,
                    up.eq(1)
                ).Elif(yn > self.step,
                    up.eq(0),
                ).Else(
                    zero.eq(1)
                )
        ]


class SweepCSR(Filter):
    def __init__(self, shift=16, **kwargs):
        Filter.__init__(self, **kwargs)

        self.submodules.limit = LimitCSR(**kwargs)

        width = flen(self.y)
        self.r_shift = CSRStatus(8, reset=shift)
        self.r_step = CSRStorage(width + shift - 1, reset=1<<shift)

        ###

        self.submodules.sweep = Sweep(width + shift)
        self.comb += [
                self.sweep.run.eq(~self.clear),
                self.sweep.step.eq(self.r_step.storage),
                self.sweep.turn.eq(self.limit.error),
                self.sweep.hold.eq(self.hold),
                self.limit.x.eq(self.sweep.y[shift:]),
                self.y.eq(self.limit.y),
        ]



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
