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

from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus

from .filter import Filter
from .limit import Limit
from .sweep import Sweep


class Relock(Filter):
    def __init__(self, step_width=None, step_shift=0, **kwargs):
        Filter.__init__(self, **kwargs)

        width = flen(self.y)
        if step_width is None:
            step_width = width

        self._shift = CSRStatus(bits_for(step_shift), reset=step_shift)
        self._step = CSRStorage(step_width)
        self._run = CSRStorage(1)
        self._min = CSRStorage(width, reset=1<<(width - 1))
        self._max = CSRStorage(width, reset=(1<<(width - 1)) - 1)

        ###

        self.submodules.sweep = Sweep(width + step_shift + 1)
        self.submodules.limit = Limit(width)

        cnt = Signal(width + step_shift + 1)
        range = Signal(max=flen(cnt))
        self.sync += [
                cnt.eq(cnt + 1),
                If(~self.error, # stop sweep, drive to zero
                    cnt.eq(0),
                    range.eq(0)
                ).Elif(self.clear | (self.sweep.y[-1] != self.sweep.y[-2]),
                    # max range if we hit limit
                    cnt.eq(0),
                    range.eq(flen(cnt) - 1)
                ).Elif(Array(cnt)[range], # 1<<range steps, turn, inc range
                    cnt.eq(0),
                    If(range != flen(cnt) - 1,
                        range.eq(range + 1)
                    )
                ),
                self.limit.min.eq(self._min.storage),
                self.limit.max.eq(self._max.storage),
                self.error.eq(self._run.storage & (self.limit.railed | self.hold)),
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
                self.sweep.step.eq(self._step.storage),
                self.sweep.run.eq(self.error),
                self.sweep.turn.eq(cnt == 0)
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
