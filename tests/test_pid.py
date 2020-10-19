from migen import run_simulation

from gateware.logic.pid import PID


def test_pid():
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

            for i in range(10):
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

            for i in range(10):
                yield
                out = yield pid.pid_out
                assert out == i

            yield pid.ki.storage.eq(-4096)

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

        yield from test_not_running()
        yield pid.running.eq(1)
        yield from test_p()
        yield from test_i()

    pid = PID(width=25)
    run_simulation(pid, pid_testbench(pid), vcd_name="pid.vcd")

