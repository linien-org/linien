from gateware.logic.sweep import SweepCSR
from gateware.logic.pid import PID
from migen import run_simulation
from gateware.linien import LinienLogic

def test_root():

    def tb(root: LinienLogic):
        sweep: SweepCSR = root.sweep
        pid: PID = root.pid

        yield sweep.step.storage.eq(1 << sweep.step_shift)
        yield sweep.run.storage.eq(1)

        yield pid.input.eq(4096)
        yield pid.kp.storage.eq(4096)
        yield pid.ki.storage.eq(0)
        yield pid.reset.storage.eq(1)

        yield

        for iteration in range(2):
            ramp_sign = (-1, 1)[iteration]

            # start the ramp and check that PID doesn't operate
            for i in range(100):
                yield
                sweep_out = yield sweep.y
                pid_out = yield pid.pid_out
                pid_running = yield pid.running

                assert sweep_out == ramp_sign * i
                assert pid_out == 0
                assert pid_running == 0

            # now turn around the ramp and request lock
            yield sweep.sweep.turn.eq(1)
            yield root.request_lock.storage.eq(1)
            yield
            yield

            # check that lock isn't turned on yet
            for i in range(102):
                yield
                sweep_out = yield sweep.y
                assert ramp_sign * sweep_out == 100 - i
                pid_running = yield pid.running
                assert pid_running == 0
                pid_out = yield pid.pid_out
                assert pid_out == 0

            if iteration == 0:
                # check that after zero crossing, PID is turned on and ramp off
                yield
                pid_running = yield pid.running
                assert pid_running == 1

                yield
                yield

                for i in range(100):
                    sweep_out = yield sweep.y
                    assert sweep_out == 0
                    pid_out = yield pid.pid_out
                    assert pid_out > 0

                yield root.request_lock.storage.eq(0)
                print('turn on ramp again')
                yield
                yield
            else:
                # in the second iteration, we approached the zero crossing from
                # the other side. In this case, we don't want to turn on the PID
                for i in range(10):
                    yield
                    sweep_out = yield sweep.y
                    print('!', sweep_out)
                    pid_running = yield pid.running
                    assert pid_running == 0



    dut = LinienLogic()
    run_simulation(dut, tb(dut), vcd_name="root.vcd")


if __name__ == '__main__':
    test_root()