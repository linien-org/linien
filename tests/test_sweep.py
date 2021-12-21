from pathlib import Path

from migen import run_simulation

from gateware.logic.sweep import SweepCSR

VCD_DIR = Path(__file__).parent / "vcd"


def test_sweep(plt):
    # s = Sweep(16)
    # from migen.fhdl import verilog
    # print(verilog.convert(s, ios=set()))

    def tb(sweep, out, n):
        yield sweep.step.storage.eq(1 << 4)
        yield sweep.max.storage.eq(1 << 10)
        yield sweep.min.storage.eq(0xFFFF & (-(1 << 10)))
        yield sweep.run.storage.eq(1)
        for i in range(3 * n):
            yield

            if i == 1.5 * n:
                yield sweep.run.storage.eq(0)
            if i == 1.5 * n + 10:
                yield sweep.run.storage.eq(1)

            out.append((yield sweep.y))
            trig.append((yield sweep.sweep.trigger))

    n = 200
    out = []
    trig = []
    dut = SweepCSR(width=16)
    run_simulation(dut, tb(dut, out, n), vcd_name=VCD_DIR / "sweep.vcd")

    plt.plot(out, label="sweep output")
    plt.plot([v * max(out) for v in trig], label=VCD_DIR / "trigger_signal")
    plt.legend()

    assert out[66] == -1024
    assert trig[66] == 1

    assert out[195] == 1024
    assert out[306] == 0
    assert out[377] == 1024
    assert out[507] == -1024
    assert trig[507] == 1

    for i in range(50):
        assert trig[i] == 0

    for i in range(400):
        assert trig[69 + i] == 0
