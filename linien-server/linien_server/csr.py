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


from . import csrmap
from .iir_coeffs import get_params


class PythonCSR:
    map = csrmap.csr
    constants = csrmap.csr_constants
    offset = 0x40300000

    def __init__(self, rp) -> None:
        self.rp = rp

    def set_one(self, addr: int, value: int) -> None:
        self.rp.write(addr, value)

    def get_one(self, addr: int):
        return int(self.rp.read(addr))

    def set(self, name: str, value: int) -> None:
        map, addr, width, wr = self.map[name]
        assert wr, name

        ma = 1 << width
        bit_mask = ma - 1
        val = value & bit_mask
        assert value == val or ma + value == val, (
            f"Value for {name} out of range",
            (value, val, ma),
        )

        b = (width + 8 - 1) // 8
        for i in range(b):
            v = (val >> (8 * (b - i - 1))) & 0xFF
            self.set_one(self.offset + (map << 11) + ((addr + i) << 2), v)

    def get(self, name: str) -> int:
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

    def set_iir(self, prefix: str, b: list[float], a: list[float]) -> None:
        shift = self.get(prefix + "_shift") or 16
        width = self.get(prefix + "_width") or 18
        bb, _, params = get_params(b, a, shift, width)

        for k in sorted(params):
            self.set(prefix + "_" + k, params[k])
        self.set(prefix + "_z0", 0)
        for i in range(len(bb), 3):
            n = prefix + f"_b{i}"
            if n in self.map:
                self.set(n, 0)
                self.set(prefix + f"_a{i}", 0)

    def states(self, *names):
        return sum(1 << csrmap.states.index(name) for name in names)
