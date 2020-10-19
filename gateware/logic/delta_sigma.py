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
        self.comb += [
            o.eq(self.data - sigma1 + (sigma2 << 1)),
            self.out.eq(o[-1])
        ]
        self.sync += [
            sigma1.eq(sigma2),
            sigma2.eq(o - (self.out << width))
        ]


class DeltaSigmaCSR(Module, AutoCSR):
    def __init__(self, out, **kwargs):
        for i, o in enumerate(out):
            ds = DeltaSigma(**kwargs)
            self.submodules += ds
            cs = CSRStorage(len(ds.data), name="data%i" % i)
            # atomic_write=True
            setattr(self, "r_data%i" % i, cs)
            self.sync += ds.data.eq(cs.storage), o.eq(ds.out)


if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt

    def tb(dut, x, y):
        for xi in x:
            yield dut.data.eq(int(xi))
            y.append((yield dut.out))
            yield
        del y[:2]

    for dut in DeltaSigma2(15), DeltaSigma(15):
        n = 1 << len(dut.data)
        #x = [j for j in range(n) for i in range(n)]
        x = (.5+.2*np.cos(.001*2*np.pi*np.arange(1 << 17)))*(n-1)
        y = []
        run_simulation(dut, tb(dut, x, y))
        #x = np.array(tb.x).reshape(-1, n)
        #y = np.array(tb.y).reshape(-1, n)
        #plt.plot(x[:, 0], x[:, 0] - y.sum(1))
        #plt.plot(y.ravel())
        plt.psd(np.array(y), detrend=plt.mlab.detrend_mean, NFFT=4096*2)
        plt.xscale("log")
    plt.show()
