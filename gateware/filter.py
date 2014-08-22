from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR


class Filter(Module, AutoCSR):
    def __init__(self, width):
        self.x = Signal((width, True))
        self.y = Signal((width, True))

        self.hold_in = Signal()
        self.clear_in = Signal()
        self.hold = Signal()
        self.clear = Signal()
        self.trigger = Signal()
        self.error = Signal()

        self.r_mode = CSRStorage(4)
        self.r_state = CSRStatus(3)
        self.r_y = CSRStatus(width)

        ###

        mode_in = Cat(self.hold_in, self.clear_in)
        mode = Cat(self.hold, self.clear)
        self.sync += [
                mode.eq((mode_in & ~self.r_mode.storage[:2]) |
                    self.r_mode.storage[2:]),
        ]
        self.comb += [
                self.r_state.status.eq(Cat(mode, self.error)),
                self.r_y.status.eq(self.y)
        ]
