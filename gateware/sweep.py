# Copyright 2014-2015 Robert Jordens <jordens@gmail.com>
#
# This file is part of redpid.
#
# redpid is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# redpid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with redpid.  If not, see <http://www.gnu.org/licenses/>.

from migen import *
from misoc.interconnect.csr import CSRStorage, CSRConstant

from .filter import Filter
from .limit import Limit


class Sweep(Module):
    def __init__(self, width):
        self.run = Signal()
        self.step = Signal(width - 1)
        self.turn = Signal()
        self.hold = Signal()
        self.y = Signal((width, True))
        self.trigger = Signal()

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
            self.trigger.eq(self.turn & up),
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

        width = len(self.y)
        if step_width is None:
            step_width = width

        self.shift = CSRConstant(step_shift, bits_for(step_shift))
        self.step = CSRStorage(step_width)
        self.min = CSRStorage(width, reset=1 << (width - 1))
        self.max = CSRStorage(width, reset=(1 << (width - 1)) - 1)
        self.run = CSRStorage(1)

        ###

        self.submodules.sweep = Sweep(width + step_shift + 1)
        self.submodules.limit = Limit(width + 1)

        min, max = self.min.storage, self.max.storage
        self.comb += [
            self.sweep.run.eq(~self.clear & self.run.storage),
            self.sweep.hold.eq(self.hold),
            self.limit.x.eq(self.sweep.y >> step_shift),
            self.sweep.step.eq(self.step.storage)
        ]
        self.sync += [
            self.limit.min.eq(Cat(min, min[-1])),
            self.limit.max.eq(Cat(max, max[-1])),
            self.sweep.turn.eq(self.limit.railed),
            self.y.eq(self.limit.y)
        ]


def main():
    from migen.fhdl import verilog
    import matplotlib.pyplot as plt

    s = Sweep(16)
    print(verilog.convert(s, ios=set()))

    def tb(sweep, out, n):
        yield sweep.step.storage.eq(1 << 4)
        yield sweep.max.storage.eq(1 << 10)
        yield sweep.min.storage.eq(0xffff & (-(1 << 10)))
        yield sweep.run.storage.eq(1)
        for i in range(n):
            yield
            out.append((yield sweep.y))

    n = 200
    out = []
    dut = SweepCSR(width=16)
    run_simulation(dut, tb(dut, out, n), vcd_name="sweep.vcd")
    plt.plot(out)
    plt.show()


if __name__ == "__main__":
    main()
