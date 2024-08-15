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
import pytest
from migen import run_simulation

from gateware.logic.pid import PID

VCD_DIR = Path(__file__).parent / "vcd"


@pytest.mark.slow
def test_pid_transfer(plt):
    def pid_testbench(pid):
        rng = np.random.default_rng(seed=299792458)
        amplitude = 0.01
        samples = 1 << 12

        x = rng.uniform(-amplitude, amplitude, samples)
        scale = 2 ** (len(pid.input) - 1) - 1
        x = (scale * np.array(x)).astype(int)
        y = np.array([0] * len(x))

        def plot_transfer(x, y, label=None):
            sampling_frequency = 125e6
            n = len(x)
            w = np.hanning(n)
            x *= w
            y *= w
            xf = np.fft.rfft(x)
            t = (np.fft.rfft(y) / xf)[:-1]
            f = (np.fft.fftfreq(n)[: n // 2 + 1] * 2)[:-1] * sampling_frequency
            _ = f[1]  # fmin
            p = plt.plot(f, 20 * np.log10(np.abs(t)), label=label)
            plot_color = p[0].get_color()
            ax = plt.gca()
            ax.set_ylim(-80, 10)
            # ax.set_xlim(fmin/2, 1.)
            ax.set_xscale("log")
            ax.set_xlabel("frequency")
            ax.set_ylabel("magnitude (dB)")
            return f, plot_color

        def plot_theory(f, p, i, d, plot_color):
            plt.plot(
                f,
                20 * np.log10(np.abs(p / 4096 + 10 * i / f + d * (f / 125e6) / (2**6))),
                color=plot_color,
                linestyle="dashed",
            )

        def do_test(p=0, i=0, d=0):
            label = f"p={p} i={i} d={d}"
            print(f"calculate label={label}")
            # unity_p = 4096
            yield pid.kp.storage.eq(p)
            yield pid.ki.storage.eq(i)
            yield pid.kd.storage.eq(d)

            yield pid.reset.storage.eq(1)

            for _ in range(10):
                yield

            yield pid.reset.storage.eq(0)
            yield pid.running.eq(1)

            for _, value in enumerate(list(x)):
                yield pid.input.eq(int(value))
                yield
                out = yield pid.pid_out
                y[_] = out

            f, plot_color = plot_transfer(x.astype(float), y.astype(float), label=label)
            plot_theory(f, p, i, d, plot_color)

        yield from do_test(p=1)
        yield from do_test(p=500)
        yield from do_test(p=8191)

        yield from do_test(i=1)
        yield from do_test(i=500)
        yield from do_test(i=8191)

        yield from do_test(d=1)
        yield from do_test(d=500)
        yield from do_test(d=8191)

        yield from do_test(p=1, i=1, d=1)
        yield from do_test(p=500, i=500, d=500)
        yield from do_test(p=8191, i=8191, d=8191)

        plt.legend(loc=(1.04, 0))
        plt.grid()
        plt.tight_layout()

    pid = PID(width=25)
    run_simulation(pid, pid_testbench(pid), vcd_name=VCD_DIR / "pid.vcd")


if __name__ == "__main__":
    test_pid_transfer()
