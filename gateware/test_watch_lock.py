from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from misoc.interconnect.csr import CSRStorage

from watch_lock import WatchLock

def testbench(watcher: WatchLock):
    time_constant = 10
    yield from watcher.time_constant.write(time_constant)
    yield from watcher.reset.write(1)
    yield from watcher.reset.write(0)

    for reset_on in (0, 1, 0):
        yield from watcher.reset.write(reset_on)

        for iteration in range(5):
            for sign in (1, -1):
                yield watcher.error_signal.eq(sign)

                for counter1 in range(time_constant - 1):
                    yield

                    counter2 = yield watcher.counter

                    if counter1 > 3:
                        if reset_on:
                            assert counter2 == 0
                        else:
                            assert counter2 == counter1 - 2
                            lock_lost_status = yield watcher.lock_lost.status
                            assert not lock_lost_status

    yield from watcher.reset.write(1)
    yield from watcher.reset.write(0)

    for i in range(time_constant):
        yield

    lock_lost = yield watcher.lock_lost.status
    assert lock_lost == 0

    for i in range(1000):
        yield
        lock_lost = yield watcher.lock_lost.status
        assert lock_lost == 1

    yield from watcher.reset.write(1)
    yield
    lock_lost = yield watcher.lock_lost.status
    assert lock_lost == 0



w = WatchLock(14)
run_simulation(w, testbench(w), vcd_name='watch_lock.vcd')