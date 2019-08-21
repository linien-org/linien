from migen import *
from misoc.interconnect.csr import CSRStorage, CSRConstant, CSRStatus, AutoCSR


class WatchLock(Module, AutoCSR):
    def __init__(self, width, max_time=int(1e6)):
        self.error_signal = Signal((width, True))

        self.reset = CSRStorage()
        self.lock_lost = CSRStatus()
        self.time_constant = CSRStorage(bits_for(max_time))

        self.counter = Signal(bits_for(max_time) + 1)
        es_sign = Signal()
        last_es_sign = Signal()

        self.sync += [
            es_sign.eq(self.error_signal > 0),
            last_es_sign.eq(es_sign),

            If(self.reset.storage,
                self.lock_lost.status.eq(0),
                self.counter.eq(0)
            ).Elif(self.lock_lost.status != 1,
                If(es_sign == last_es_sign,
                    self.counter.eq(self.counter + 1)
                ).Else(
                    self.counter.eq(0)
                ),

                If(self.counter >= self.time_constant.storage,
                    self.lock_lost.status.eq(1)
                ),
            )
        ]