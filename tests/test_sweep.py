from migen import run_simulation
import matplotlib.pyplot as plt
from gateware.logic.sweep import Sweep, SweepCSR

def test_sweep():
    #s = Sweep(16)
    #from migen.fhdl import verilog
    #print(verilog.convert(s, ios=set()))

    def tb(sweep, out, n):
        yield sweep.step.storage.eq(1 << 4)
        yield sweep.max.storage.eq(1 << 10)
        yield sweep.min.storage.eq(0xffff & (-(1 << 10)))
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
    run_simulation(dut, tb(dut, out, n), vcd_name="sweep.vcd")

    if False:
        plt.plot(out, label='ramp output')
        plt.plot([v * max(out) for v in trig], label='trigger_signal')
        plt.legend()
        plt.show()

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


