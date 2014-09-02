# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.misc import optree
from migen.bank.description import AutoCSR, CSRStorage

from .iir import Iir
from .limit import LimitCSR
from .sweep import SweepCSR
from .relock import Relock
from .modulate import Modulate, Demodulate


class FastChain(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25, coeff_width=18):
        self.adc = Signal((width, True))
        self.dac = Signal((width, True))

        self.r_x_tap = CSRStorage(2)
        self.r_break = CSRStorage(1)
        self.r_y_tap = CSRStorage(2)

        x_hold = Signal()
        x_clear = Signal()
        x_sat = Signal()
        x_railed = Signal()
        y_hold = Signal()
        y_clear = Signal()
        y_sat = Signal()
        y_railed = Signal()
        relock = Signal()
        unlocked = Signal()

        self.state_in = x_hold, x_clear, y_hold, y_clear, relock
        self.state_out = x_sat, x_railed, y_sat, y_railed, unlocked

        x = Signal((signal_width, True))
        dx = Signal((signal_width, True))
        y = Signal((signal_width, True))
        dy = Signal((signal_width, True))
        rx = Signal((signal_width, True))

        self.signal_in = dx, dy, rx
        self.signal_out = x, y

        ###

        self.submodules.iir_a = Iir(width=signal_width,
                coeff_width=coeff_width, shift=coeff_width-2,
                order=1)
        self.submodules.demod = Demodulate(width=width)
        self.submodules.iir_b = Iir(width=signal_width,
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
        self.submodules.x_limit = LimitCSR(width=signal_width, guard=1)
        self.submodules.iir_c = Iir(width=signal_width,
                coeff_width=coeff_width, shift=coeff_width-2,
                order=1)
        self.submodules.iir_d = Iir(width=signal_width,
                coeff_width=coeff_width, shift=coeff_width-2,
                order=2)
        self.submodules.iir_e = Iir(width=signal_width,
                coeff_width=2*coeff_width-1, order=2,
                shift=2*coeff_width-3, mode="iterative")
        self.submodules.relock = Relock(width=width + 1, step_width=24,
                step_shift=16)
        self.submodules.sweep = SweepCSR(width=width, step_width=24,
                step_shift=18)
        self.submodules.mod = Modulate(width=width)
        self.submodules.y_limit = LimitCSR(width=width, guard=3)

        ###

        s = signal_width - width
        self.comb += [
                self.iir_a.x.eq(self.adc << s),
                self.iir_a.hold.eq(x_hold),
                self.iir_a.clear.eq(x_clear),

                self.demod.x.eq(self.iir_a.y >> s),
                self.demod.phase.eq(self.mod.phase),

                self.iir_b.x.eq(self.demod.y << s),
                self.iir_b.hold.eq(x_hold),
                self.iir_b.clear.eq(x_clear),

                x_sat.eq(
                    (self.iir_a.error & (self.r_x_tap.storage > 0)) |
                    (self.iir_b.error & (self.r_x_tap.storage > 2))
                ),

        ]
        xs = Array([self.iir_a.x, self.iir_a.y,
                self.iir_b.x, self.iir_b.y])
        self.sync += x.eq(xs[self.r_x_tap.storage])
        self.comb += [
                self.x_limit.x.eq(Mux(self.r_break.storage, 0, x) + dx),
                x_railed.eq(self.x_limit.error),

                self.iir_c.x.eq(self.x_limit.y),
                self.iir_c.hold.eq(y_hold),
                self.iir_c.clear.eq(y_clear),

                self.iir_d.x.eq(self.iir_c.y),
                self.iir_d.hold.eq(y_hold),
                self.iir_d.clear.eq(y_clear),

                self.iir_e.x.eq(self.iir_d.y),
                self.iir_e.hold.eq(y_hold),
                self.iir_e.clear.eq(y_clear),

                y_sat.eq(
                    (self.iir_c.error & (self.r_y_tap.storage > 1)) |
                    (self.iir_d.error & (self.r_y_tap.storage > 2)) |
                    (self.iir_e.error & (self.r_y_tap.storage > 3))
                ),

                self.sweep.clear.eq(0),
                self.sweep.hold.eq(0),

                self.relock.x.eq(rx >> s),
                self.relock.clear.eq(self.y_limit.error),
                self.relock.hold.eq(relock),
                unlocked.eq(self.relock.error)
        ]
        ya = Signal((width + 3, True))
        ys = Array([self.iir_c.x, self.iir_c.y,
                    self.iir_d.y, self.iir_e.y])
        self.sync += ya.eq(optree("+", [self.mod.y, dy >> s, self.sweep.y,
                    self.relock.y])),
        self.comb += [
                self.y_limit.x.eq((ys[self.r_y_tap.storage] >> s) + ya),
                y.eq(self.y_limit.y << s),
                y_railed.eq(self.y_limit.error),

                self.dac.eq(self.y_limit.y)
        ]


class SlowChain(Module, AutoCSR):
    def __init__(self, width=16, signal_width=25, coeff_width=18):
        self.adc = Signal((width, True))
        self.dac = Signal((width, True))

        hold = Signal()
        clear = Signal()
        sat = Signal()
        railed = Signal()

        self.r_break = CSRStorage(1)

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
        self.submodules.y_limit = LimitCSR(width=width, guard=1)

        ###

        s = signal_width - width
        self.comb += [
                x.eq(self.adc << s),
                self.x_limit.x.eq(Mux(self.r_break.storage, 0, x) + dx),
                self.iir.x.eq(self.x_limit.y),
                self.iir.hold.eq(hold),
                self.iir.clear.eq(clear),
                sat.eq(self.iir.error),
                self.y_limit.x.eq((self.iir.y >> s) + (dy >> s)),
                railed.eq(self.y_limit.error),
                y.eq(self.y_limit.y << s),
                self.dac.eq(y >> s)
        ]


def cross_connect(gpio, chains):
    state_names = ["force"] + ["di%i" % i for i in range(flen(gpio.i))]
    states = [1, gpio.i]
    signal_names = ["zero"]
    signals = Array([0])
    for n, c in chains:
        states.extend(c.state_out)
        state_names += ["%s_%s" % (n, s.backtrace[-1][0])
                for s in c.state_out]
        signals.extend(c.signal_out)
        signal_names += ["%s_%s" % (n, s.backtrace[-1][0])
                for s in c.signal_out]
    states = Cat(states)
    state = Signal(flen(states))
    gpio.comb += state.eq(states)
    for i, s in enumerate(gpio.o):
        name = "do%i_en" % i
        csr = CSRStorage(flen(state), name=name)
        setattr(gpio, name, csr)
        gpio.sync += s.eq((state & csr.storage) != 0)
    for n, c in chains:
        for s in c.state_in:
            name = s.backtrace[-1][0] + "_en"
            en = CSRStorage(flen(state), name=name)
            setattr(c, name, en)
            name = s.backtrace[-1][0] + "_inv"
            inv = CSRStorage(flen(state), name=name)
            setattr(c, name, inv)
            c.sync += s.eq(((state ^ inv.storage) & en.storage) != 0)
        for s in c.signal_in:
            name = s.backtrace[-1][0] + "_sel"
            sel = CSRStorage(bits_for(len(signals)), name=name)
            setattr(c, name, sel)
            c.sync += s.eq(signals[sel.storage])
    return state_names, signal_names
