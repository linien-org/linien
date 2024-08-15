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

import numpy as np
from migen import run_simulation

from gateware.logic.delta_sigma import DeltaSigma, DeltaSigma2


def test_delta_sigma(plt):
    def tb(dut, x, y):
        for xi in x:
            yield dut.data.eq(int(xi))
            y.append((yield dut.out))
            yield
        del y[:2]

    for dut in DeltaSigma2(15), DeltaSigma(15):
        n = 1 << len(dut.data)
        # x = [j for j in range(n) for i in range(n)]
        x = (0.5 + 0.2 * np.cos(0.001 * 2 * np.pi * np.arange(1 << 17))) * (n - 1)
        y = []
        run_simulation(dut, tb(dut, x, y))
        # x = np.array(tb.x).reshape(-1, n)
        # y = np.array(tb.y).reshape(-1, n)
        # plt.plot(x[:, 0], x[:, 0] - y.sum(1))
        # plt.plot(y.ravel())
        plt.psd(np.array(y), detrend=plt.mlab.detrend_mean, NFFT=4096 * 2)
        plt.xscale("log")
