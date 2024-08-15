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

import numpy as np
from migen import run_simulation

from gateware.logic.pid import PID

VCD_DIR = Path(__file__).parent / "vcd"


def test_pid(plt):
    def pid_testbench(pid):
        def test_not_running():
            input_ = 1000
            yield pid.input.eq(input_)
            unity_p = 4096
            yield pid.kp.storage.eq(unity_p)
            yield pid.ki.storage.eq(unity_p)
            yield pid.kd.storage.eq(unity_p)

            for i in range(10):
                yield
                out = yield pid.pid_out
                assert out == 0

        def test_p():
            input_ = 1000
            yield pid.input.eq(input_)

            unity_p = 4096
            yield pid.kp.storage.eq(unity_p)
            yield pid.ki.storage.eq(0)
            yield pid.kd.storage.eq(0)

            for _ in range(10):
                yield

            out = yield pid.pid_out
            assert out == input_

            yield pid.kp.storage.eq(int(unity_p / 2))

            for i in range(10):
                yield

            out = yield pid.pid_out
            assert out == input_ / 2

        def test_i():
            input_ = 1024
            yield pid.input.eq(input_)

            yield pid.kp.storage.eq(0)
            yield pid.ki.storage.eq(0)
            yield pid.kd.storage.eq(0)

            for i in range(10):
                yield

            yield pid.ki.storage.eq(4096)
            yield

            for i in range(10):
                yield
                out = yield pid.pid_out
                assert out == i

            yield pid.ki.storage.eq(-4096)
            yield
            yield

            for i in range(20):
                yield
                out = yield pid.pid_out
                assert out == 10 - i

            yield pid.ki.storage.eq(-8192)
            yield pid.input.eq(pid.max_pos)
            for i in range(1000):
                yield

            out = yield pid.pid_out
            int_out = yield pid.int_out
            assert out == int_out
            assert out == pid.max_neg

            yield pid.input.eq(pid.max_neg)

            for i in range(2000):
                yield

            out = yield pid.pid_out
            int_out = yield pid.int_out
            assert out == int_out
            assert out == pid.max_pos

        def test_d():
            ys = []
            for offset in (0, 2000):
                x = offset + (np.sin(np.linspace(-np.pi, np.pi, 100)) * 4000).astype(
                    int
                )
                y = []

                yield pid.ki.storage.eq(0)
                yield pid.kp.storage.eq(0)
                yield pid.kd.storage.eq(8191)

                for v in x:
                    yield pid.input.eq(int(v))
                    yield
                    out = yield pid.pid_out
                    y.append(out)

                plt.plot(x)
                plt.plot(y)

                ys.append(y)

            assert np.all(np.abs(np.array(ys[0][10:]) - np.array(ys[1][10:])) <= 1)

        yield from test_not_running()
        yield pid.running.eq(1)
        yield from test_p()
        yield from test_i()
        yield from test_d()

    pid = PID(width=25)
    run_simulation(pid, pid_testbench(pid), vcd_name=VCD_DIR / "pid.vcd")


if __name__ == "__main__":
    test_pid()
