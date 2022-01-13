from pathlib import Path

import pytest
from migen import run_simulation

from gateware.logic.sweep import SweepCSR

VCD_DIR = Path(__file__).parent / "vcd"


@pytest.fixture
def dut():
    return SweepCSR(width=16)


def test_simple_sweep(dut, plt):
    """Tests a single sweep."""

    n = 200
    y = []
    turn = []
    trigger = []
    up = []

    def testbench():
        yield dut.step.storage.eq(1 << 4)
        yield dut.min.storage.eq(0xFFFF & (-(1 << 10)))
        yield dut.max.storage.eq(1 << 10)
        yield dut.run.storage.eq(1)
        for _ in range(n):
            y.append((yield dut.y))
            turn.append((yield dut.sweep.turn))
            trigger.append((yield dut.sweep.trigger))
            up.append((yield dut.sweep.up))
            yield

    run_simulation(dut, testbench(), vcd_name=VCD_DIR / "test_simple_sweep.vcd")

    # Wrap plotting in try-except to avoid pytest errors if --plot option is not passed.
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
        yield dut.step.storage.eq(1 << 4)
        yield dut.min.storage.eq(0xFFFF & (-(1 << 10)))
        yield dut.max.storage.eq(1 << 10)
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

    # Wrap plotting in try-except to avoid pytest errors if --plot option is not passed.
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
    change_min_max_at = [0, 10, 80, 120, 180, 200, 250]

    def testbench():
        yield dut.step.storage.eq(1 << 4)
        yield dut.min.storage.eq(0xFFFF & (-(1 << 10)))
        yield dut.max.storage.eq(1 << 10)
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
            if i == change_min_max_at[4]:
                # change min and max to the same value
                yield dut.min.storage.eq(100)
                yield dut.max.storage.eq(100)
            if i == change_min_max_at[5]:
                # back to different range including the current value
                # BUG: This doesn't work. `dut.sweep.up` stays 1 and the output rails at
                # the maximum value.
                yield dut.min.storage.eq(0)
                yield dut.max.storage.eq(200)
            if i == change_min_max_at[6]:
                # BUG: However, this works.
                yield dut.min.storage.eq(0)
                yield dut.max.storage.eq(1100)
            y.append((yield dut.y))
            up.append((yield dut.sweep.up))
            yield

    run_simulation(dut, testbench(), vcd_name=VCD_DIR / "test_change_sweep_min_max.vcd")

    # Wrap plotting in try-except to avoid pytest errors if --plot option is not passed.
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
    for val in y[change_min_max_at[3] + 3 : change_min_max_at[4]]:
        assert val >= -200
        assert val <= 0

    # test that constant value is set:
    for val in y[change_min_max_at[4] + 3 : change_min_max_at[5]]:
        assert val == 100

    # test that values are changing again and are within the new range:
    y_changed = False
    previous_y = y[change_min_max_at[5] + 3]
    for val in y[change_min_max_at[5] + 3 : change_min_max_at[6]]:
        assert val >= 0
        assert val <= 200
        if val != previous_y:
            y_changed = True
        previous_y = val
    # This test currently fails.
    assert y_changed

    # test that values are changing again and are within the new range (2nd time):
    y_changed = False
    previous_y = y[change_min_max_at[6] + 3]
    for val in y[change_min_max_at[6] + 3 : change_min_max_at[-1]]:
        assert val >= 0
        assert val <= 1100
        if val != previous_y:
            y_changed = True
        previous_y = val
    # This works.
    assert y_changed
