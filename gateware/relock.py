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
from .sweep import Sweep


class Relock(Filter):
    def __init__(self, step_width=None, step_shift=0, **kwargs):
        Filter.__init__(self, **kwargs)

        width = len(self.y)
        if step_width is None:
            step_width = width

        self.shift = CSRConstant(step_shift, bits_for(step_shift))
        self.step = CSRStorage(step_width)
        self.run = CSRStorage(1)
        self.min = CSRStorage(width, reset=1 << (width - 1))
        self.max = CSRStorage(width, reset=(1 << (width - 1)) - 1)

        ###

        self.submodules.sweep = Sweep(width + step_shift + 1)
        self.submodules.limit = Limit(width)

        cnt = Signal(width + step_shift + 1)
        range = Signal(max=len(cnt))
        self.sync += [
            cnt.eq(cnt + 1),
            If(~self.error,  # stop sweep, drive to zero
                cnt.eq(0),
                range.eq(0)
            ).Elif(self.clear | (self.sweep.y[-1] != self.sweep.y[-2]),
                # max range if we hit limit
                cnt.eq(0),
                range.eq(len(cnt) - 1)
            ).Elif(Array(cnt)[range],  # 1<<range steps, turn, inc range
                cnt.eq(0),
                If(range != len(cnt) - 1,
                    range.eq(range + 1)
                )
            ),
            self.limit.min.eq(self.min.storage),
            self.limit.max.eq(self.max.storage),
            self.error.eq(self.run.storage & (self.limit.railed | self.hold)),
            If(self.sweep.y[-1] == self.sweep.y[-2],
                self.y.eq(self.sweep.y >> step_shift)
            )
        ]
        self.comb += [
            # relock at limit.railed or trigger if not prevented by hold
            # stop sweep at not relock
            # drive error on relock to hold others
            # turn at range or clear (from final limiter)
            self.limit.x.eq(self.x),
            self.sweep.step.eq(self.step.storage),
            self.sweep.run.eq(self.error),
            self.sweep.turn.eq(cnt == 0)
        ]


def tb(relock, x, y):
    yield relock.run.storage.eq(1)
    yield relock.step.storage.eq(1 << 8)
    yield relock.max.storage.eq(1024)
    yield relock.min.storage.eq(0xffff & -1024)

    for i in range(2000):
        yield
        if i < 200:
            yield relock.x.eq(0xffff & -2000)
        elif i < 400:
            yield relock.x.eq(2000)
        elif i < 900:
            yield relock.x.eq(0)
        if (yield relock.y) > 3000:
            yield relock.limit.railed.eq(1)
        elif (yield relock.y) < -3000:
            yield relock.limit.railed.eq(2)
        else:
            yield relock.limit.railed.eq(0)
        x.append((yield relock.x))
        y.append((yield relock.y))


def main():
    from migen.fhdl import verilog
    import matplotlib.pyplot as plt

    s = Relock(width=16)
    print(verilog.convert(s, ios=set()))

    dut = Relock(width=16)
    x, y = [], []
    run_simulation(dut, tb(dut, x, y), vcd_name="relock.vcd")
    plt.plot(x)
    plt.plot(y)
    plt.show()


if __name__ == "__main__":
    main()
