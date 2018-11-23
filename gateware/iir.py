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
from migen.genlib.misc import timeline
from misoc.interconnect.csr import CSRStorage, CSRConstant

from .filter import Filter


class Iir(Filter):
    def __init__(self, order=1, mode="pipelined",
                 width=25, coeff_width=18,
                 shift=16, intermediate_width=None):
        Filter.__init__(self, width)
        assert mode in ("pipelined", "iterative")
        if intermediate_width is None:
            intermediate_width = width + coeff_width
            # + bits_for(2*(order + 1))

        self.z0 = CSRStorage(intermediate_width - shift, reset=0)
        self.shift = CSRConstant(shift)
        self.width = CSRConstant(coeff_width)
        self.interval = CSRConstant(0, 8)
        self.latency = CSRConstant(0, 8)
        self.order = CSRConstant(order, 8)
        self.iterative = CSRConstant(mode == "iterative", 1)

        self.c = c = {}
        for i in "ab":
            for j in range(order + 1):
                name = "%s%i" % (i, j)
                if name == "a0":
                    continue
                ci = Signal((coeff_width, True), name=name)
                rci = CSRStorage(len(ci), name=name)
                self.sync += ci.eq(rci.storage)
                c[name] = ci
                setattr(self, "r_" + name, rci)

        ###

        z = Signal((intermediate_width, True), name="z0r")
        self.sync += z.eq(self.z0.storage << shift)

        y_lim = Signal.like(self.y)
        y_next = Signal.like(z)
        skip = shift+width-1
        y_over = y_next[skip:]
        y_pat = Signal.like(y_over, reset=2**(intermediate_width - skip) - 1)
        y = Signal.like(self.y)
        railed = Signal()
        self.comb += [
            railed.eq(~((y_over == y_pat) | (y_over == ~y_pat))),
            If(railed,
                y_lim.eq(self.y)
            ).Else(
                y_lim.eq(y_next[shift:])
            )
        ]
        self.sync += [
            self.error.eq(railed),
            self.y.eq(y_lim),
            If(self.clear,
                y.eq(0)
            ).Elif(~self.hold,
                y.eq(y_lim)
            )
        ]

        if mode == "pipelined":
            r = [("b%i" % i, self.x) for i in reversed(range(order + 1))]
            r += [("a%i" % i, y) for i in reversed(range(1, order + 1))]
            for coeff, signal in r:
                zr = Signal.like(z)
                self.sync += zr.eq(z)
                z = Signal.like(zr)
                self.comb += z.eq(zr + signal*c[coeff])
            self.comb += y_next.eq(z)
            self.latency.value = Constant(order + 1)
            self.interval.value = Constant(1)

        elif mode == "iterative":
            ma = Signal.like(self.y)
            mb = Signal.like(c["a1"])
            mm = Signal.like(z)
            mc = Signal.like(z)
            mp = Signal.like(z)
            self.sync += mm.eq(ma*mb), mc.eq(mp)
            self.comb += mp.eq(mm + mc)
            steps = []
            x = [self.x] + [Signal.like(self.x) for i in range(order + 1)]
            for i in reversed(range(order + 1)):
                steps.append([
                    x[i + 1].eq(x[i]), ma.eq(x[i]), mb.eq(c["b%i" % i])
                ])
            y = [None, y] + [Signal.like(y) for i in range(1, order + 1)]
            for i in reversed(range(1, order + 1)):
                steps.append([
                    y[i + 1].eq(y[i]), ma.eq(y[i]), mb.eq(c["a%i" % i])
                ])
            steps[1].append(mc.eq(z))
            latency = order + 4
            if order == 1:
                steps.append([])
                latency += 1
            self.latency.value = Constant(latency)
            steps[int(order > 1)].append(y_next.eq(mp))
            self.sync += timeline(1, list(enumerate(steps)))
            self.interval.value = Constant(len(steps))

        else:
            raise ValueError
