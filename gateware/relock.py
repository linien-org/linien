from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR


class Relock(Module, AutoCSR):
    def __init__(self, signal_width=16, step_width=32):
        guard = step_width - width

        self.stop = Signal()
        self.x = Signal((width, True))
        self.y = Signal((width, True))
        self.minval = Signal((width, True))
        self.maxval = Signal((width, True))
        self.step = Signal((step_width, True))
        amplitude = Signal((step_width, True))
        self.railed = Signal(2)
        self.hold_in = Signal()
        self.hold_out = Signal()
        hi = Signal()
        lo = Signal()
        locked = Signal()
        direction = Signal()
        y = Signal((step_width, True))

        self.comb += [
                locked.eq((self.x >= self.minval) & (self.x <= self.maxval)),
                self.hold_out.eq(~self.stop & ~locked),
                self.y.eq(y >> guard),
                hi.eq(y >= amplitude),
                lo.eq(y <= -amplitude),
                ]
        self.sync += [
                If(~self.hold_in,
                    If(locked, # drive to zero
                        amplitude.eq(0),
                        If(y < -self.step,
                            y.eq(y + self.step),
                        ).Elif(y > self.step,
                            y.eq(y - self.step),
                        ).Else(
                            y.eq(0),
                        ),
                    ).Else( # triangle
                        If(direction == 0,
                            y.eq(y + self.step),
                        ).Else(
                            y.eq(y - self.step),
                        ),
                        If(amplitude == 0, # initialize triangle
                            amplitude.eq(self.step << 4),
                        ),
                        If(self.railed[0] | hi,
                            direction.eq(1), # turn around
                            If((direction == 0) & ~amplitude[-1], # double amp
                                amplitude.eq(amplitude << 1),
                            ),
                        ).Elif(self.railed[1] | lo,
                            direction.eq(0), # turn around
                        ),
                    ),
                ),
                If(self.stop,
                    y.eq(0),
                    direction.eq(0),
                    amplitude.eq(0),
                )]



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
