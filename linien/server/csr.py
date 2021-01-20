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


import csrmap
from iir_coeffs import get_params, make_filter


class PitayaCSR:
    map = csrmap.csr
    constants = csrmap.csr_constants
    offset = 0x40300000

    def set(self, name, value):
        map, addr, width, wr = self.map[name]
        assert wr, name

        ma = 1 << width
        bit_mask = ma - 1
        val = value & bit_mask
        assert value == val or ma + value == val, (
            "value for %s out of range" % name,
            (value, val, ma),
        )

        b = (width + 8 - 1) // 8
        for i in range(b):
            v = (val >> (8 * (b - i - 1))) & 0xFF
            self.set_one(self.offset + (map << 11) + ((addr + i) << 2), v)

    def get(self, name):
        if name in self.constants:
            return self.constants[name]

        map, addr, nr, wr = self.map[name]
        v = 0
        b = (nr + 8 - 1) // 8
        for i in range(b):
            v |= self.get_one(self.offset + (map << 11) + ((addr + i) << 2)) << 8 * (
                b - i - 1
            )
        return v

    def set_iir(self, prefix, b, a, z=0):
        shift = self.get(prefix + "_shift") or 16
        width = self.get(prefix + "_width") or 18
        interval = self.get(prefix + "_interval") or 1
        b, a, params = get_params(b, a, shift, width, interval)

        for k in sorted(params):
            self.set(prefix + "_" + k, params[k])
        self.set(prefix + "_z0", z)
        for i in range(len(b), 3):
            n = prefix + "_b%i" % i
            if n in self.map:
                self.set(n, 0)
                self.set(prefix + "_a%i" % i, 0)

    def signal(self, name):
        return csrmap.signals.index(name)

    def states(self, *names):
        return sum(1 << csrmap.states.index(name) for name in names)


class PythonCSR(PitayaCSR):
    def __init__(self, rp):
        self.rp = rp

    def set_one(self, addr, value):
        self.rp.write(addr, value)

    def get_one(self, addr):
        return int(self.rp.read(addr))
