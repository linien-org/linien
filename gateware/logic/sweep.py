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

from migen import Signal, If, Cat, bits_for, Module
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

        self.up = Signal()
        turning = Signal()
        dir = Signal()

        self.comb += [
            If(self.run,
                If(self.turn & ~turning,
                    self.up.eq(~dir)
                ).Else(
                    self.up.eq(dir)
                )
            ).Else(
                self.up.eq(1)
            )
        ]
        self.sync += [
            self.trigger.eq(self.turn & self.up),
            turning.eq(self.turn),
            dir.eq(self.up),
            If(~self.run,
                self.y.eq(0)
            ).Elif(~self.hold,
                If(self.up,
                    self.y.eq(self.y + self.step),
                ).Else(
                    self.y.eq(self.y - self.step),
                )
            )
        ]


class SweepCSR(Filter):
    def __init__(self, step_width=None, step_shift=0, **kwargs):
        Filter.__init__(self, **kwargs)

        # required by tests
        self.step_shift = step_shift

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
