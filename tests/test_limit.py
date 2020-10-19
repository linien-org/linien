from migen import run_simulation
from gateware.logic.limit import Limit

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
    run_simulation(dut, tb(dut, n), vcd_name="limit.vcd")
