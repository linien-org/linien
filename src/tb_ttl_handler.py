from migen import *
from ttl_handler import TTLHandler


# sync(2) + edge detect(1) + SNAPSHOT(1) + TRIGGER(1) = 5 cycles min.
# add margin for test reliability.
REACT_CYCLES = 10


def tb_ttl_handler():
    dut = TTLHandler()

    def run(dut):

        #helpers
        def set_linien(pid, integ, sweep, dac):
            yield dut.i_linien_pid_out.eq(pid)
            yield dut.i_linien_integrator.eq(integ)
            yield dut.i_linien_sweep_pos.eq(sweep)
            yield dut.i_linien_dac_out.eq(dac)

        def send_ttl(width=2):
            yield dut.i_ttl.eq(1)
            for _ in range(width):
                yield
            yield dut.i_ttl.eq(0)

        def wait(n):
            for _ in range(n):
                yield

        #setup
        yield from set_linien(pid=1000, integ=500000, sweep=4000, dac=3000)
        yield

        #test 1: disabled
        print("test 1:  trigger ignored when disabled")
        yield dut.i_enable.eq(0)
        yield
        yield from send_ttl()
        yield from wait(REACT_CYCLES)
        assert (yield dut.o_active) == 0
        assert (yield dut.o_fsm_start) == 0
        print("  passed")

        #test 2: enable + trigger + snapshot
        print("test 2:  enable, trigger, check snapshot")
        yield dut.i_enable.eq(1)
        yield; yield
        yield from send_ttl()
        yield from wait(REACT_CYCLES)

        assert (yield dut.o_active) == 1
        assert (yield dut.o_saved_pid_out) == 1000
        assert (yield dut.o_saved_integrator) == 500000
        assert (yield dut.o_saved_sweep_pos) == 4000
        print("  passed")

        #test 3: dac_out captured
        print("test 3:  o_saved_dac_out captures starting voltage")
        assert (yield dut.o_saved_dac_out) == 3000
        print("  passed")

        #test 4: o_fsm_start is not stuck
        print("test 4:  o_fsm_start is exactly one cycle (not stuck high)")
        assert (yield dut.o_fsm_start) == 0
        print("  passed")

        #test 5: active holds
        print("test 5:  o_active holds during sequence")
        for i in range(50):
            yield
            assert (yield dut.o_active) == 1, f"dropped at cycle {i}"
        print("  passed")

        #test 6: seq_done releases
        print("test 6:  i_seq_done releases o_active")
        yield dut.i_seq_done.eq(1)
        yield
        yield dut.i_seq_done.eq(0)
        yield; yield

        assert (yield dut.o_active) == 0
        print("  passed")

        #test 7: re-trigger with new values
        print("test 7:  re-trigger with new linien values")
        yield from set_linien(pid=2000, integ=800000, sweep=6000, dac=5000)
        yield; yield

        yield from send_ttl()
        yield from wait(REACT_CYCLES)

        assert (yield dut.o_active) == 1
        assert (yield dut.o_saved_pid_out) == 2000
        assert (yield dut.o_saved_integrator) == 800000
        assert (yield dut.o_saved_sweep_pos) == 6000
        assert (yield dut.o_saved_dac_out) == 5000
        print("  passed")

        #test 8: double-trigger ignored
        print("test 8:  second edge during active is ignored")
        yield from set_linien(pid=9999, integ=111111, sweep=7777, dac=8888)
        yield

        yield from send_ttl()
        yield from wait(REACT_CYCLES)

        # snapshot should still be from test 7
        assert (yield dut.o_saved_pid_out) == 2000
        assert (yield dut.o_saved_dac_out) == 5000
        print("  passed")

        #test 9: disable mid-sequence doesn't interrupt
        print("test 9:  disable during active doesn't drop o_active")
        yield dut.i_enable.eq(0)
        yield from wait(10)
        assert (yield dut.o_active) == 1
        yield dut.i_enable.eq(1)
        print("  passed")

        # cleanup from tests 7-9
        yield dut.i_seq_done.eq(1)
        yield
        yield dut.i_seq_done.eq(0)
        yield from wait(3)
        assert (yield dut.o_active) == 0

        #test 10: 1-cycle TTL pulse
        print("test 10: 1-cycle TTL pulse still detected")
        yield from set_linien(pid=3000, integ=900000, sweep=5000, dac=4500)
        yield dut.i_enable.eq(1)
        yield; yield

        yield from send_ttl(width=1)
        yield from wait(REACT_CYCLES)

        assert (yield dut.o_active) == 1
        assert (yield dut.o_saved_pid_out) == 3000
        print("  passed")

        # cleanup
        yield dut.i_seq_done.eq(1)
        yield
        yield dut.i_seq_done.eq(0)
        yield from wait(3)

        #test 11: TTL held high for many cycles: only triggers once
        print("test 11: TTL held high doesn't re-trigger")
        yield from set_linien(pid=4000, integ=100000, sweep=2000, dac=1500)
        yield dut.i_enable.eq(1)
        yield; yield

        # hold TTL high for 20 cycles
        yield dut.i_ttl.eq(1)
        yield from wait(20)
        yield dut.i_ttl.eq(0)
        yield from wait(REACT_CYCLES)

        assert (yield dut.o_active) == 1
        assert (yield dut.o_saved_pid_out) == 4000

        # finish sequence
        yield dut.i_seq_done.eq(1)
        yield
        yield dut.i_seq_done.eq(0)
        yield from wait(3)
        assert (yield dut.o_active) == 0

        #check: does it trigger again? TTL is already low so shouldn't.
        yield from wait(REACT_CYCLES)
        assert (yield dut.o_active) == 0, "should not re-trigger after TTL dropped"
        print("  passed")

        #test 12: status bits
        print("test 12: status bits")
        yield dut.i_enable.eq(1)
        yield
        status = yield dut.o_status
        assert status & 0b01 == 0, "active should be 0"
        assert status & 0b10 == 2, "armed should be 1"

        yield dut.i_enable.eq(0)
        yield
        status = yield dut.o_status
        assert status == 0, f"should be 0 when disabled, got {status}"
        print("  passed")

        print("\nall 12 tests passed")

    run_simulation(dut, run(dut), vcd_name="ttl_handler.vcd")


if __name__ == "__main__":
    tb_ttl_handler()