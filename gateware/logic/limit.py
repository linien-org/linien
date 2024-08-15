# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

from migen import Cat, If, Module, Replicate, Signal
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
            If(
                self.x >= self.max,
                self.y.eq(self.max),
                self.railed.eq(1),
            )
            .Elif(
                self.x <= self.min,
                self.y.eq(self.min),
                self.railed.eq(1),
            )
            .Else(
                self.y.eq(self.x),
                self.railed.eq(0),
            )
        ]


class LimitCSR(Filter):
    def __init__(self, guard=0, **kwargs):
        Filter.__init__(self, **kwargs)

        width = len(self.y)
        if guard:
            self.x = Signal((width + guard, True))
        self.min = CSRStorage(width, reset=1 << (width - 1))
        self.max = CSRStorage(width, reset=(1 << (width - 1)) - 1)

        ###

        self.submodules.limit = Limit(width + guard)

        min, max = self.min.storage, self.max.storage
        if guard:
            min = Cat(min, Replicate(min[-1], guard))
            max = Cat(max, Replicate(max[-1], guard))
        self.comb += [self.limit.x.eq(self.x)]
        self.sync += [
            self.limit.min.eq(min),
            self.limit.max.eq(max),
            self.y.eq(self.limit.y),
            self.error.eq(self.limit.railed),
        ]
