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

from linien_common.common import AutolockMode
from migen import run_simulation

from gateware.linien_module import LinienLogic
from gateware.logic.pid import PID
from gateware.logic.sweep import SweepCSR

VCD_DIR = Path(__file__).parent / "vcd"


def test_root():
    def tb(root: LinienLogic, lock_target_position):
        print("lock target position", lock_target_position)
        sweep: SweepCSR = root.sweep
        pid: PID = root.pid
        autolock = root.autolock
        fast = autolock.fast
        yield autolock.autolock_mode.storage.eq(AutolockMode.SIMPLE)

        yield fast.target_position.storage.eq(lock_target_position)

        yield sweep.step.storage.eq(1 << sweep.step_shift)
        yield sweep.run.storage.eq(1)

        yield pid.input.eq(4096)
        yield pid.kp.storage.eq(4096)
        yield pid.ki.storage.eq(0)
        yield pid.reset.storage.eq(1)

        yield

        for iteration in range(2):
            print("iteration", iteration)
            sweep_sign = (-1, 1, -1)[iteration]

            sweep_out_at_beginning = yield sweep.y

            # start the sweep and check that PID doesn't operate
            for i in range(100 - sweep_out_at_beginning):
                yield
                sweep_out = yield sweep.y
                pid_out = yield pid.pid_out
                pid_running = yield pid.running

                assert sweep_out == sweep_out_at_beginning + sweep_sign * i
                assert pid_out == 0
                assert pid_running == 0

            # now turn around the sweep and request lock
            yield sweep.sweep.turn.eq(1)
            yield autolock.request_lock.storage.eq(1)
            yield
            yield

            # check that lock isn't turned on yet
            for i in range(102 + lock_target_position):
                yield
                sweep_out = yield sweep.y
                assert sweep_sign * sweep_out == 100 - i
                pid_running = yield pid.running
                assert pid_running == 0
                pid_out = yield pid.pid_out
                assert pid_out == 0

            if iteration == 0:
                # check that after zero crossing, PID is turned on and sweep off
                yield

                autolock_requested = yield autolock.request_lock.storage
                fast_turn_on = yield fast.turn_on_lock

                assert autolock_requested
                assert fast_turn_on

                pid_running = yield pid.running
                sweep_out = yield sweep.y
                assert pid_running == 1

                yield
                yield

                sweep_out_at_begin_of_lock = yield sweep.y
                assert sweep_out_at_begin_of_lock == 3 + lock_target_position

                for i in range(100):
                    sweep_out = yield sweep.y
                    assert sweep_out == sweep_out_at_begin_of_lock
                    pid_out = yield pid.pid_out
                    assert pid_out > 0

                yield autolock.request_lock.storage.eq(0)
                print("turn on sweep again")
                yield
                yield
            else:
                # in the second iteration, we approached the zero crossing from
                # the other side. In this case, we don't want to turn on the PID
                for i in range(10):
                    yield
                    sweep_out = yield sweep.y
                    pid_running = yield pid.running
                    assert pid_running == 0

    dut = LinienLogic()
    run_simulation(
        dut, tb(dut, lock_target_position=0), vcd_name=VCD_DIR / "root_target0.vcd"
    )
    dut = LinienLogic()
    run_simulation(
        dut, tb(dut, lock_target_position=-40), vcd_name=VCD_DIR / "root_target-40.vcd"
    )
    dut = LinienLogic()
    run_simulation(dut, tb(dut, 51), vcd_name=VCD_DIR / "root_target_51.vcd")


if __name__ == "__main__":
    test_root()
