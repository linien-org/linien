from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus

from .filter import Filter
from .limit import LimitCSR
from .sweep import Sweep


class Relock(Filter):
    def __init__(self, shift=16, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        self.submodules.limit = LimitCSR(width=width)

        self.r_shift = CSRStatus(8, reset=shift)
        self.r_step = CSRStorage(width + shift - 1, reset=1<<shift)

        ###

        self.submodules.sweep = Sweep(width + shift)

        cnt = Signal(width + shift - 1)
        range = Signal(max=width + shift - 1)
        self.sync += [
                cnt.eq(cnt + 1),
                If(~self.sweep.run,
                    cnt.eq(0),
                    range.eq(0)
                ).Elif(self.clear | (cnt == (1 << range)),
                    cnt.eq(0),
                    If(range < width + shift - 2,
                        range.eq(range + 1)
                    )
                ),
        ]

        self.comb += [
                self.error.eq(self.limit.error),
                self.limit.x.eq(self.x),
                self.sweep.run.eq(~self.hold & (self.error | self.trigger)),
                self.sweep.step.eq(self.r_step.storage),
                self.sweep.turn.eq(cnt == 0),
                self.y.eq(self.sweep.y[shift:])
        ]


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.relock = Relock(**kwargs)
        self.x = []
        self.y = []

    def do_simulation(self, s):
        if s.cycle_counter == 0:
            s.wr(self.relock.step, 1<<21)
            s.wr(self.relock.maxval, 1024)
            s.wr(self.relock.minval, 0xffff&-1024)
        elif s.cycle_counter < 200:
            s.wr(self.relock.x, 0xffff&-2000)
        elif s.cycle_counter < 400:
            s.wr(self.relock.x, 2000)
        elif s.cycle_counter > 900:
            s.wr(self.relock.x, 0)
        if s.rd(self.relock.y) > 3000:
            s.wr(self.relock.railed, 1)
        elif s.rd(self.relock.y) < -3000:
            s.wr(self.relock.railed, 2)
        else:
            s.wr(self.relock.railed, 0)
        self.x.append(s.rd(self.relock.x))
        self.y.append(s.rd(self.relock.y))


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel
    import matplotlib.pyplot as plt

    s = Relock()
    print(verilog.convert(s, ios=set()))

    n = 2000
    tb = TB()
    sim = Simulator(tb, TopLevel("relock.vcd"))
    sim.run(n)
    plt.plot(tb.x)
    plt.plot(tb.y)
    plt.show()


if __name__ == "__main__":
    main()
