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
from misoc.interconnect.csr import CSRStorage

from .filter import Filter


class Limit(Module):
    def __init__(self, width):
        self.x = Signal((width, True))
        self.y = Signal.like(self.x)
        self.max = Signal.like(self.x)
        self.min = Signal.like(self.x)
        self.railed = Signal()

        ###

        self.comb += [
            If(self.x >= self.max,
                self.y.eq(self.max),
                self.railed.eq(1)
            ).Elif(self.x <= self.min,
                self.y.eq(self.min),
                self.railed.eq(1)
            ).Else(
                self.y.eq(self.x),
                self.railed.eq(0)
            )
        ]


class LimitCSR(Filter):
    def __init__(self, guard=0, **kwargs):
        Filter.__init__(self, **kwargs)

        width = len(self.y)
        if guard:
            self.x = Signal((width + guard, True))
        self._min = CSRStorage(width, reset=1 << (width - 1))
        self._max = CSRStorage(width, reset=(1 << (width - 1)) - 1)

        ###

        self.submodules.limit = Limit(width + guard)

        min, max = self._min.storage, self._max.storage
        if guard:
            min = Cat(min, Replicate(min[-1], guard))
            max = Cat(max, Replicate(max[-1], guard))
        self.comb += [
            self.limit.x.eq(self.x)
        ]
        self.sync += [
            self.limit.min.eq(min),
            self.limit.max.eq(max),
            self.y.eq(self.limit.y),
            self.error.eq(self.limit.railed)
        ]


def main():
    from migen.fhdl import verilog
    import matplotlib.pyplot as plt

    s = Limit(16)
    print(verilog.convert(s, ios=set()))

    def tb(limit, x, y, n):
        yield limit.maxval.eq(1 << 10)
        yield limit.minval(-(1 << 10))
        for i in range(n):
            yield
            yield limit.x.eq(-2*(yield limit.maxval) + (c << 6))
            x.append((yield limit.x))
            y.append((yield limit.y))

    dut = Limit(16)
    n = 1 << 6
    x, y = [], []
    run_simulation(dut, tb(dut, x, y, n), vcd_name="limit.vcd")
    plt.plot(x)
    plt.plot(y)
    plt.show()


if __name__ == "__main__":
    main()
