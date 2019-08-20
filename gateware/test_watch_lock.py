import random

from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from misoc.interconnect.csr import CSRStorage

from watch_lock import WatchLock

def testbench(watcher: WatchLock):
    time_constant = 1000
    yield from watcher.time_constant.write(time_constant)
    yield from watcher.threshold.write(int(.1 * time_constant))
    yield from watcher.reset.write(1)
    yield from watcher.reset.write(0)

    for reset_on in (0, 1, 0):
        yield from watcher.reset.write(reset_on)

        for even in (True, False):
            for iteration in range(5):
                for t in range(time_constant):
                    if even:
                        yield watcher.error_signal.eq(random.choice([-1, 1]))
                    else:
                        yield watcher.error_signal.eq(random.choice(
                            ([-1] * 12) + [1] * 10
                        ))
                    yield

                    lock_lost_status = yield watcher.lock_lost.status

                    if even:
                        assert not lock_lost_status

            if reset_on:
                assert not lock_lost_status
            else:
                if not even:
                    assert lock_lost_status

    yield from watcher.reset.write(1)
    yield
    lock_lost = yield watcher.lock_lost.status
    assert lock_lost == 0



w = WatchLock(14)
run_simulation(w, testbench(w), vcd_name='watch_lock.vcd')