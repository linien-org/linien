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

from pathlib import Path

from migen import run_simulation

from gateware.logic.limit import Limit

VCD_DIR = Path(__file__).parent / "vcd"


def test_limit():
    def tb(limit, n):
        m = 1 << 10
        yield limit.max.eq(m)
        yield limit.min.eq(-m)

        yield limit.x.eq(-2000)
        yield
        out = yield limit.y
        assert out == -m

        yield limit.x.eq(2000)
        yield
        out = yield limit.y
        assert out == m

        yield limit.x.eq(-1000)
        yield
        out = yield limit.y
        assert out == -1000

        yield limit.x.eq(1000)
        yield
        out = yield limit.y
        assert out == 1000

        yield limit.x.eq(0)
        yield
        out = yield limit.y
        assert out == 0

    dut = Limit(16)
    n = 1 << 6
    run_simulation(dut, tb(dut, n), vcd_name=VCD_DIR / "limit.vcd")
