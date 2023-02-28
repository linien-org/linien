# Copyright 2014-2015 Robert Jördens <jordens@gmail.com>
# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
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

from migen import Module, Signal
from misoc.interconnect.csr import AutoCSR, CSRStorage


class DeltaSigma(Module):
    def __init__(self, width=12):
        self.data = Signal(width)
        self.out = Signal()

        ###

        delta = Signal(width + 1)
        sigma = Signal(width + 1)
        self.comb += delta.eq(self.out << width)
        self.sync += sigma.eq(self.data - delta + sigma)
        self.comb += self.out.eq(sigma[-1])


class DeltaSigma2(Module):
    def __init__(self, width=12):
        self.data = Signal(width)
        self.out = Signal()

        ###

        sigma1 = Signal(width + 3)
        sigma2 = Signal(width + 3)
        o = Signal(width + 3)
        self.comb += [o.eq(self.data - sigma1 + (sigma2 << 1)), self.out.eq(o[-1])]
        self.sync += [sigma1.eq(sigma2), sigma2.eq(o - (self.out << width))]


class DeltaSigmaCSR(Module, AutoCSR):
    def __init__(self, out, **kwargs):
        for i, o in enumerate(out):
            ds = DeltaSigma(**kwargs)
            self.submodules += ds
            cs = CSRStorage(len(ds.data), name="data%i" % i)
            # atomic_write=True
            setattr(self, "r_data%i" % i, cs)
            self.sync += ds.data.eq(cs.storage), o.eq(ds.out)
