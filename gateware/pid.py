# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *

from .filter import Filter
from .iir import Iir
from .limit import LimitCSR, Limit
from .sweep import SweepCSR
from .relock import Relock
from .modulate import Modulate, Demodulate


class FastChain(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25, coeff_width=18):
        self.adc = Signal((width, True))
        self.dac = Signal((width, True))

        self.r_x_tap = CSRStorage(3)
        self.r_x_zero = CSRStorage(1)
        self.r_y_tap = CSRStorage(2)

        x_hold = Signal()
        x_clear = Signal()
        x_sat = Signal()
        x_railed = Signal()
        y_hold = Signal()
        y_clear = Signal()
        y_sat = Signal()
        y_railed = Signal()
        y_relock = Signal()
        y_unlocked = Signal()

        self.state_in = x_hold, x_clear, y_hold, y_clear, y_relock
        self.state_out = x_sat, x_railed, y_sat, y_railed, y_unlocked

        x = Signal((signal_width, True))
        dx = Signal((signal_width, True))
        y = Signal((signal_width, True))
        dy = Signal((signal_width, True))
        r = Signal((signal_width, True))

        self.signal_in = dx, r
        self.signal_out = x, y
        self.dy = dy

        ###

        self.submodules.iir_a = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.iir_b = Iir(width=signal_width,
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
        self.submodules.demod = Demodulate(width=width)
        self.submodules.x_limit = LimitCSR(width=signal_width, guard=1)
        self.submodules.iir_c = Iir(width=signal_width,
                coeff_width=coeff_width, order=1)
        self.submodules.iir_d = Iir(width=signal_width,
                coeff_width=coeff_width, order=2)
        self.submodules.iir_e = Iir(width=signal_width,
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
        self.submodules.relock = Relock(width=width + 1, step_width=24,
                step_shift=16)
        self.submodules.sweep = SweepCSR(width=width, step_width=24,
                step_shift=18)
        self.submodules.mod = Modulate(width=width)
        self.submodules.y_limit = LimitCSR(width=signal_width, guard=3)

        ###

        s = signal_width - width
        self.comb += [
                self.iir_a.x.eq(self.adc << s),
                self.iir_a.hold.eq(x_hold),
                self.iir_a.clear.eq(x_clear),

                self.iir_b.x.eq(self.iir_a.y),
                self.iir_b.hold.eq(x_hold),
                self.iir_b.clear.eq(x_clear),

                x_sat.eq(
                    (self.iir_a.error & self.r_x_tap.storage > 0) |
                    (self.iir_b.error & self.r_x_tap.storage > 1)
                ),

                self.demod.x.eq(Mux(self.r_x_tap.storage[0],
                    self.iir_a.y >> s, self.iir_b.y >> s)),
                self.demod.phase.eq(self.mod.phase)
        ]
        xs = Array([self.iir_a.x, self.iir_a.y, self.iir_b.y,
                    self.demod.y << s, self.demod.y << s])
        self.sync += [
                x.eq(xs[self.r_x_tap.storage]),
                x_railed.eq(self.x_limit.error),
                self.iir_c.x.eq(self.x_limit.y)
        ]
        self.comb += [
                self.x_limit.x.eq(Mux(self.r_x_zero.storage, 0, x) + dx),

                self.iir_c.hold.eq(y_hold),
                self.iir_c.clear.eq(y_clear),

                self.iir_d.x.eq(self.iir_c.y),
                self.iir_d.hold.eq(y_hold),
                self.iir_d.clear.eq(y_clear),

                self.iir_e.x.eq(self.iir_d.y),
                self.iir_e.hold.eq(y_hold),
                self.iir_e.clear.eq(y_clear),

                y_sat.eq(
                    (self.iir_c.error & self.r_y_tap.storage > 0) |
                    (self.iir_d.error & self.r_y_tap.storage > 1) |
                    (self.iir_e.error & self.r_y_tap.storage > 2)
                )
        ]
        ya = Signal((width + 3, True))
        ys = Array([self.iir_c.x, self.iir_c.y,
                    self.iir_d.y, self.iir_e.y])
        self.sync += [
                ya.eq(optree("+", [self.mod.y, dy, self.sweep.y,
                    self.relock.y])),
                self.y_limit.x.eq(ys[self.r_y_tap.storage] + ya)
        ]
        self.comb += [
                y.eq(self.y_limit.y),
                y_railed.eq(self.y_limit.error),

                self.relock.x.eq(r),
                self.relock.clear.eq(self.y_limit.error),
                self.relock.hold.eq(y_relock),
                y_unlocked.eq(self.relock.error),

                self.dac.eq(self.y_limit.y >> s),
        ]


class SlowChain(Module, AutoCSR):
    def __init__(self, width=16, signal_width=25, coeff_width=18):
        self.adc = Signal((width, True))
        self.dac = Signal((width, True))

        hold = Signal()
        clear = Signal()
        sat = Signal()
        railed = Signal()

        self.r_x_zero = CSRStorage(1)

        x = Signal((signal_width, True))
        dx = Signal((signal_width, True))
        y = Signal((signal_width, True))
        dy = Signal((signal_width, True))

        self.state_in = hold, clear
        self.state_out = sat, railed
        self.signal_in = dx,
        self.signal_out = x, y

        ###

        self.submodules.x_limit = LimitCSR(width=signal_width, guard=1)
        self.submodules.iir = Iir(width=signal_width,
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
        #self.submodules.sweep = SweepCSR(width=width, step_width=24,
        #        step_shift=18)
        self.submodules.y_limit = LimitCSR(width=signal_width, guard=1)

        ###

        s = signal_width - width
        self.comb += [
                x.eq(self.adc << s),
                self.x_limit.x.eq(Mux(self.r_x_zero.storage, 0, x) + dx),
                self.iir.x.eq(self.x_limit.y),
                self.iir.hold.eq(hold),
                self.iir.clear.eq(clear),
                sat.eq(self.iir.error),
                self.y_limit.x.eq(self.iir.y + dy),
                railed.eq(self.y_limit.error),
                y.eq(self.y_limit.y),
                self.dac.eq(y >> s)
        ]


def cross_connect(gpio, chains):
    states = [1, gpio.i]
    signals = Array([0])
    for c in chains:
        states.extend(c.state_out)
        signals.extend(c.signal_out)
    states = Cat(states)
    state = Signal(flen(states))
    gpio.comb += state.eq(states)
    for i, s in enumerate(gpio.o):
        name = "do%i_en" % i
        csr = CSRStorage(flen(state), name=name)
        setattr(gpio, name, csr)
        gpio.comb += s.eq((state & csr.storage) != 0)
    for c in chains:
        for s in c.state_in:
            name = s.backtrace[-1][0] + "_en"
            csr = CSRStorage(flen(state), name=name)
            setattr(c, name, csr)
            c.comb += s.eq((state & csr.storage) != 0)
        for s in c.signal_in:
            name = s.backtrace[-1][0] + "_mux"
            csr = CSRStorage(len(signals), name=name)
            setattr(c, name, csr)
            c.sync += s.eq(signals[csr.storage])
