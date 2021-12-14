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
        yield dut.max.storage.eq(1 << 10)
        yield dut.min.storage.eq(0xFFFF & (-(1 << 10)))
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
    n = 300
    y = []
    run = []
    up = []

    # clock clycles at switch run status is changed.
    switch_run_at = [10, 210, 250, 280]

    def testbench():
        yield dut.step.storage.eq(1 << 4)
        yield dut.max.storage.eq(1 << 10)
        yield dut.min.storage.eq(0xFFFF & (-(1 << 10)))
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
