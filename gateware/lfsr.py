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

from functools import reduce
from operator import xor

from migen import *
from misoc.interconnect.csr import AutoCSR, CSRStorage


class LFSR(Module):
    """many-to-one (external xor, fibonacci style)
    xnor (exclude all-ones)
    no extended sequence
    """
    def __init__(self, n=31, taps=[27, 30]):
        self.o = Signal()

        ###

        state = Signal(n)
        self.comb += self.o.eq(~reduce(xor, [state[i] for i in taps]))
        self.sync += Cat(state).eq(Cat(self.o, state))


class LFSRGen(Module, AutoCSR):
    def __init__(self, width, n=31):
        y = Signal((width, True))
        self.signal_out = y,
        self.signal_in = ()
        self.state_in = ()
        self.state_out = ()

        self.bits = CSRStorage(bits_for(width))

        taps = {
            7: (6, 5),
            15: (14, 13),
            31: (30, 27),
            63: (62, 61),
        }[n]

        self.submodules.gen = LFSR(n, taps)
        cnt = Signal(max=width + 1)
        store = Signal(width)
        self.sync += [
            store.eq(Cat(self.gen.o, store)),
            cnt.eq(cnt + 1),
            If(cnt == self.bits.storage,
                cnt.eq(1),
                y.eq(store),
                store.eq(Replicate(self.gen.o, flen(store)))
            )
        ]


class XORSHIFT(Module):
    def __init__(self, n=32, shifts=[13, -17, 5], reset=2463534242):
        self.state = Signal(n, reset=reset)

        ###

        i = self.state
        for s in shifts:
            i0 = i
            i = Signal.like(i0)
            if s > 0:
                self.comb += i.eq(i0 ^ (i0 << s))
            else:
                self.comb += i.eq(i0 ^ (i0 >> -s))
        self.sync += self.state.eq(i)


class XORSHIFTGen(Module, AutoCSR):
    def __init__(self, width, **kwargs):
        y = Signal((width, True))
        self.signal_out = y,
        self.signal_in = ()
        self.state_in = ()
        self.state_out = ()

        self.bits = CSRStorage(bits_for(width))

        self.submodules.gen = XORSHIFT(**kwargs)
        q = Signal(width)
        self.sync += [
            q.eq(self.gen.state[:width] >> (width - self.bits.storage)),
            y.eq(q[1:] ^ (Replicate(q[0], width)))
        ]


if __name__ == "__main__":
    from migen.fhdl import verilog

    lfsr = LFSR(4, [3, 2])
    print(verilog.convert(lfsr, ios={lfsr.o}))

    def tb(dut, o, n):
        for i in range(n):
            yield
            o.append((yield dut.o))

    dut = LFSR(4, [3, 0])
    o = []
    run_simulation(dut, tb(dut, o, 20))
    print(o)

    import matplotlib.pyplot as plt
    import numpy as np

    def tb(dut, o, n):
        for i in range(n):
            yield
            o.append((yield dut.state))

    dut = XORSHIFT()
    o = []
    run_simulation(dut, tb(dut, o, 1 << 12))
    o = np.array(o)
    o = o/2.**len(dut.state) - .5
    plt.psd(o)
    #plt.hist(o)
    plt.show()
