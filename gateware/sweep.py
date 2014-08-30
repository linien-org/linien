from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus

from .filter import Filter
from .limit import Limit


class Sweep(Module):
    def __init__(self, width):
        self.run = Signal()
        self.step = Signal(width - 1)
        self.turn = Signal()
        self.hold = Signal()
        self.y = Signal((width, True))

        ###

        up = Signal()
        zero = Signal()
        turning = Signal()
        dir = Signal()

        self.comb += [
                If(self.run,
                    If(self.turn & ~turning,
                        up.eq(~dir)
                    ).Else(
                        up.eq(dir)
                    )
                ).Else(
                    If(self.y < 0,
                        up.eq(1)
                    ).Elif(self.y > self.step,
                        up.eq(0)
                    ).Else(
                        zero.eq(1)
                    )
                )
        ]
        self.sync += [
                turning.eq(self.turn),
                dir.eq(up),
                If(zero,
                    self.y.eq(0)
                ).Elif(~self.hold,
                    If(up,
                        self.y.eq(self.y + self.step),
                    ).Else(
                        self.y.eq(self.y - self.step),
                    )
                )
        ]


class SweepCSR(Filter):
    def __init__(self, step_width=None, step_shift=0, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        if step_width is None:
            step_width = width

        self.r_shift = CSRStatus(bits_for(step_shift), reset=step_shift)
        self.r_step = CSRStorage(step_width)
        self.r_min = CSRStorage(width, reset=1<<(width - 1))
        self.r_max = CSRStorage(width, reset=(1<<(width - 1)) - 1)
        self.r_run = CSRStorage(1)

        ###

        self.submodules.sweep = Sweep(width + step_shift + 1)
        self.submodules.limit = Limit(width + 1)

        min, max = self.r_min.storage, self.r_max.storage
        self.comb += [
                self.sweep.run.eq(~self.clear & self.r_run.storage),
                self.sweep.hold.eq(self.hold),
                self.limit.x.eq(self.sweep.y >> step_shift),
                self.sweep.step.eq(self.r_step.storage)
        ]
        self.sync += [
                self.limit.min.eq(Cat(min, min[-1])),
                self.limit.max.eq(Cat(max, max[-1])),
                self.sweep.turn.eq(self.limit.railed),
                self.y.eq(self.limit.y)
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
