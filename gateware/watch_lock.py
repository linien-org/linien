from migen import *
from misoc.interconnect.csr import CSRStorage, CSRConstant, CSRStatus, AutoCSR


class WatchLock(Module, AutoCSR):
    def __init__(self, width, max_time=int(1e6)):
        self.error_signal = Signal((width, True))

        self.reset = CSRStorage()
        self.lock_lost = CSRStatus()

        self.time_constant = CSRStorage(bits_for(max_time))
        self.threshold = CSRStorage(bits_for(max_time))

        self.value = Signal((bits_for(max_time) + 1, True))
        self.counter = Signal(bits_for(max_time))

        self.sync += [
            If(self.reset.storage,
                self.lock_lost.status.eq(0),
                self.value.eq(0),
                self.counter.eq(0)
            ).Elif(self.lock_lost.status != 1,
                If(self.counter < self.time_constant.storage,
                    self.counter.eq(self.counter + 1),

                    If(self.error_signal > 0,
                        self.value.eq(self.value + 1)
                    ).Elif(self.error_signal < 0,
                        self.value.eq(self.value - 1)
                    ),
                ).Else(
                    self.counter.eq(0),
                    self.value.eq(0),
                    If(
                            (self.value > self.threshold.storage)
                            | (self.value < -1 * self.threshold.storage),
                        self.lock_lost.status.eq(1),
                    )
                )
            )
        ]