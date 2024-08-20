# This file is part of Linien and based on redpid.#
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

import pytest
from migen import run_simulation

from gateware.logic.sweep import SweepCSR

VCD_DIR = Path(__file__).parent / "vcd"


@pytest.fixture
def dut():
    return SweepCSR(width=14)


def test_simple_sweep(dut, plt):
    """Tests a single sweep."""

    n = 200
    y = []
    turn = []
    trigger = []
    up = []

    def testbench():
        yield dut.step.storage.eq(16)
        yield dut.min.storage.eq(-1024)
        yield dut.max.storage.eq(1024)
        yield dut.run.storage.eq(1)
        for _ in range(n):
            y.append((yield dut.y))
            turn.append((yield dut.sweep.turn))
            trigger.append((yield dut.sweep.trigger))
            up.append((yield dut.sweep.up))
            yield

    run_simulation(dut, testbench(), vcd_name=VCD_DIR / "test_simple_sweep.vcd")

    # Wrap in try-except to avoid pytest errors if --plots option is not passed.
    try:
        _, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, sharex=True)
        ax1.plot(y, label="y")
        ax1.set_ylabel("y")
        ax2.plot(turn, label="turn")
        ax2.set_ylabel("turn")
        ax3.plot(up, label="up")
        ax3.set_ylabel("up")
        ax4.plot(trigger, label="trigger")
        ax4.set_ylabel("trigger")
    except ValueError:
        pass

    # test start of sweep
    assert y[0:3] == [0, 0, 0]
    assert turn[0:3] == [0, 1, 0]
    assert up[0:3] == [1, 0, 0]

    # test at minimum
    assert y[66:69] == [-1024, -1024, -1024]
    assert turn[65:70] == [0, 1, 1, 1, 0]
    assert up[66:196] == 130 * [1]
    assert trigger[66:71] == [0, 1, 1, 1, 0]

    # test at maximum
    assert y[196:199] == [1024, 1024, 1024]
    assert turn[196:199] == [1, 1, 1]


def test_sweep_start_stop(dut, plt):
    """Tests that the sweep can be started and stopped."""
    n = 300
    y = []
    run = []
    up = []

    # clock clycles at switch run status is changed.
    switch_run_at = [10, 210, 250, 280]

    def testbench():
        yield dut.step.storage.eq(16)
        yield dut.min.storage.eq(-1024)
        yield dut.max.storage.eq(1024)
        yield dut.run.storage.eq(0)
        for i in range(n):
            if i == switch_run_at[0]:
                yield dut.run.storage.eq(1)
            elif i == switch_run_at[1]:
                yield dut.run.storage.eq(0)
            elif i == switch_run_at[2]:
                yield dut.run.storage.eq(1)
            elif i == switch_run_at[3]:
                yield dut.run.storage.eq(0)

            y.append((yield dut.y))
            run.append((yield dut.sweep.run))
            up.append((yield dut.sweep.up))
            yield

    run_simulation(dut, testbench(), vcd_name=VCD_DIR / "test_sweep_start_stop.vcd")

    # Wrap in try-except to avoid pytest errors if --plots option is not passed.
    try:
        _, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True)
        ax1.plot(y, label="y")
        ax1.set_ylabel("y")
        ax2.plot(run, label="run")
        ax2.set_ylabel("run")
        ax3.plot(up, label="up")
        ax3.set_ylabel("up")
    except ValueError:
        pass

    # test initial state (not running)
    for i in range(switch_run_at[0]):
        assert run[i] == 0
        assert up[i] == 1
        assert y[i] == 0

    # test switching on
    assert run[switch_run_at[0] : switch_run_at[0] + 2] == [0, 1]
    assert y[switch_run_at[0] + 1 : switch_run_at[0] + 4] == [0, 0, 16]

    # test switching off
    assert run[switch_run_at[1] : switch_run_at[1] + 2] == [1, 0]
    assert y[switch_run_at[1] + 2] != 0
    assert y[switch_run_at[1] + 3] == 0


def test_change_sweep_min_max(dut, plt):
    """Tests that the sweep minimum and maximum can be changed."""
    n = 350
    y = []
    up = []
    change_min_max_at = [0, 10, 80, 120]

    def testbench():
        yield dut.step.storage.eq(16)
        yield dut.min.storage.eq(-1024)
        yield dut.max.storage.eq(1024)
        yield dut.run.storage.eq(1)
        for i in range(n):
            if i == change_min_max_at[1]:
                # change min while going down and before reaching new value
                yield dut.min.storage.eq(-500)
            if i == change_min_max_at[2]:
                # change max while going up and after crossing new value
                yield dut.max.storage.eq(100)
            if i == change_min_max_at[3]:
                # change min and max to a new region that does not include the current
                # value
                yield dut.min.storage.eq(-200)
                yield dut.max.storage.eq(0)
            y.append((yield dut.y))
            up.append((yield dut.sweep.up))
            yield

    run_simulation(dut, testbench(), vcd_name=VCD_DIR / "test_change_sweep_min_max.vcd")

    # Wrap in try-except to avoid pytest errors if --plots option is not passed.
    try:
        _, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
        ax1.plot(y, label="y")
        ax1.set_ylabel("y")
        ax2.plot(up, label="up")
        ax2.set_ylabel("up")
        for val in change_min_max_at[1:]:
            ax1.axvline(val, color="r")
    except ValueError:
        pass

    # 3 clock cycles are needed to reach the new min/max values.
    # test minimum is changed correctly:
    for val in y[change_min_max_at[1] + 3 : change_min_max_at[2]]:
        assert val >= -500

    # test maximum is changed correctly (3 clock cycles to ):
    for val in y[change_min_max_at[2] + 3 : change_min_max_at[3]]:
        assert val <= 100

    # test minimum and maximum are changed correctly:
    for val in y[change_min_max_at[3] + 3 : change_min_max_at[-1]]:
        assert val >= -200
        assert val <= 0


def test_pause_sweep(dut, plt):
    """Tests that the sweep can be paused and resumed."""

    n = 150
    y = []
    pause = []

    def testbench():
        yield dut.step.storage.eq(16)
        yield dut.min.storage.eq(-1024)
        yield dut.max.storage.eq(1024)
        yield dut.run.storage.eq(1)
        for i in range(n):
            if i == 50:
                # pause sweep
                yield dut.pause.storage.eq(1)

            if i == 100:
                # resume sweep
                yield dut.pause.storage.eq(0)

            y.append((yield dut.y))
            pause.append((yield dut.pause.storage))
            yield

    run_simulation(dut, testbench(), vcd_name=VCD_DIR / "test_pause_sweep.vcd")

    # Wrap in try-except to avoid pytest errors if --plots option is not passed.
    try:
        _, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
        ax1.plot(y, label="y")
        ax1.set_ylabel("y")
        ax2.plot(pause, label="pause")
        ax2.set_ylabel("pause")
    except ValueError:
        pass

    # test that the sweep is paused
    assert y[52:59] == 7 * [0]
    # test that the sweep is resumed
    previous_y = 0
    for val in y[102:105]:
        assert val != 0
        assert val != previous_y
        previous_y = val
