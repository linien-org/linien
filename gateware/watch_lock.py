from migen import *
from misoc.interconnect.csr import CSRStorage, CSRConstant, CSRStatus, AutoCSR


class WatchLock(Module, AutoCSR):
    def __init__(self, width, max_time=int(1e6)):
        self.error_signal = Signal((width, True))

        self.reset = CSRStorage()
        self.lock_lost = CSRStatus()
        self.time_constant = CSRStorage(bits_for(max_time))
        self.threshold = CSRStorage(width)

        self.counter = Signal(bits_for(max_time) + 1)

        last = Signal((width, True))
        # FIXME: real mean
        mean = Signal((width, True))

        self.sync += [
            mean.eq(self.error_signal),
            If(self.reset.storage,
                self.counter.eq(0),
                self.lock_lost.status.eq(0)
            ).Else(
                If(self.counter < self.time_constant.storage,
                    self.counter.eq(self.counter + 1)
                ).Else(
                    If(
                            ((mean - last) > self.threshold.storage)
                            | ((last - mean) > self.threshold.storage),
                        self.lock_lost.status.eq(1)
                    ),
                    self.counter.eq(0),
                )
            )
        ]