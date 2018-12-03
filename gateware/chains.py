# Copyright 2014-2015 Robert Jordens <jordens@gmail.com>
#
# This file is part of redpid.
#
# redpid is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# redpid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with redpid.  If not, see <http://www.gnu.org/licenses/>.

from migen import *
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus, CSR

from .iir import Iir
from .limit import LimitCSR
from .sweep import SweepCSR
from .relock import Relock
from .modulate import Modulate, Demodulate


class FastChain(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25, coeff_width=18):
        self.adc = Signal((width, True))
        self.dac = Signal((width, True))

        self.x_tap = CSRStorage(2)
        self.brk = CSRStorage(1)
        self.y_tap = CSRStorage(2)

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
        sweep_trigger = Signal()

        self.state_in = x_hold, x_clear, y_hold, y_clear, relock
        self.state_out = x_sat, x_railed, y_sat, y_railed, unlocked

        x = Signal((signal_width, True))
        dx = Signal((signal_width, True))
        y = Signal((signal_width, True))
        dy = Signal((signal_width, True))
        rx = Signal((signal_width, True))

        self.signal_in = dx, dy, rx
        self.signal_out = x, y, sweep_trigger

        ###

        self.submodules.iir_a = Iir(
            width=signal_width, coeff_width=coeff_width, shift=coeff_width-2,
            order=1)
        self.submodules.demod = Demodulate(width=width)
        self.submodules.iir_b = Iir(
            width=2*coeff_width, coeff_width=signal_width,
            shift=signal_width-2, order=2, mode="iterative")
        self.submodules.x_limit = LimitCSR(width=signal_width, guard=1)
        self.submodules.iir_c = Iir(
            width=signal_width, coeff_width=coeff_width, shift=coeff_width-2,
            order=1)
        self.submodules.iir_d = Iir(
            width=signal_width, coeff_width=coeff_width, shift=coeff_width-2,
            order=2)
        self.submodules.iir_e = Iir(
            width=2*coeff_width, coeff_width=signal_width,
            shift=signal_width-2, order=2, mode="iterative")
        self.submodules.relock = Relock(
            width=width + 1, step_width=24, step_shift=16)
        self.submodules.sweep = SweepCSR(
            width=width, step_width=24, step_shift=18)
        self.submodules.mod = Modulate(width=width)
        self.submodules.y_limit = LimitCSR(width=width, guard=3)

        ###

        s = signal_width - width
        s1 = 2*coeff_width - width
        s2 = 2*coeff_width - signal_width
        self.comb += [
            self.iir_a.x.eq(self.adc << s),
            self.iir_a.hold.eq(x_hold),
            self.iir_a.clear.eq(x_clear),

            self.demod.x.eq(self.iir_a.y >> s),
            self.demod.phase.eq(self.mod.phase),

            self.iir_b.x.eq(self.demod.y << s1),
            self.iir_b.hold.eq(x_hold),
            self.iir_b.clear.eq(x_clear),

            x_sat.eq(
                (self.iir_a.error & (self.x_tap.storage > 0)) |
                (self.iir_b.error & (self.x_tap.storage > 2))
            ),
        ]
        xs = Array([self.iir_a.x, self.iir_a.y,
                    self.iir_b.x >> s2, self.iir_b.y >> s2])
        self.sync += x.eq(xs[self.x_tap.storage])
        self.comb += [
            self.x_limit.x.eq(Mux(self.brk.storage, 0, x) + dx),
            x_railed.eq(self.x_limit.error),

            self.iir_c.x.eq(self.x_limit.y),
            self.iir_c.hold.eq(y_hold),
            self.iir_c.clear.eq(y_clear),

            self.iir_d.x.eq(self.iir_c.y),
            self.iir_d.hold.eq(y_hold),
            self.iir_d.clear.eq(y_clear),

            self.iir_e.x.eq(self.iir_d.y << s2),
            self.iir_e.hold.eq(y_hold),
            self.iir_e.clear.eq(y_clear),

            y_sat.eq(
                (self.iir_c.error & (self.y_tap.storage > 1)) |
                (self.iir_d.error & (self.y_tap.storage > 2)) |
                (self.iir_e.error & (self.y_tap.storage > 3))
            ),

            self.sweep.clear.eq(0),
            self.sweep.hold.eq(0),
            sweep_trigger.eq(self.sweep.sweep.trigger),

            self.relock.x.eq(rx >> s),
            self.relock.clear.eq(self.y_limit.error),
            self.relock.hold.eq(relock),
            unlocked.eq(self.relock.error)
        ]
        ya = Signal((width + 3, True))
        ys = Array([self.iir_c.x, self.iir_c.y,
                    self.iir_d.y, self.iir_e.y >> s2])
        self.sync += ya.eq(
            (self.mod.y + (dy >> s)) +
            (self.sweep.y + self.relock.y)),
        self.comb += [
            self.y_limit.x.eq((ys[self.y_tap.storage] >> s) + ya),
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

        self.brk = CSRStorage(1)

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
        self.submodules.iir = Iir(
            width=2*coeff_width, coeff_width=signal_width, order=2,
            shift=signal_width-2, mode="iterative")
        #self.submodules.sweep = SweepCSR(width=width, step_width=24,
        #        step_shift=18)
        self.submodules.y_limit = LimitCSR(width=width, guard=1)

        ###

        s = signal_width - width
        s1 = 2*coeff_width - signal_width
        s2 = 2*coeff_width - width
        self.comb += [
            x.eq(self.adc << s),
            self.x_limit.x.eq(Mux(self.brk.storage, 0, x) + dx),
            self.iir.x.eq(self.x_limit.y << s1),
            self.iir.hold.eq(hold),
            self.iir.clear.eq(clear),
            sat.eq(self.iir.error),
            self.y_limit.x.eq((self.iir.y >> s2) + (dy >> s)),
            railed.eq(self.y_limit.error),
            y.eq(self.y_limit.y << s),
            self.dac.eq(y >> s)
        ]


def cross_connect(gpio, chains):
    state_names = ["force"] + ["di%i" % i for i in range(len(gpio.i))]
    states = [1, gpio.i]
    signal_names = ["zero"]
    signals = Array([0])

    for n, c in chains:
        for s in c.state_out:
            states.append(s)
            state_names.append("%s_%s" % (n, s.backtrace[-1][0]))
        for s in c.signal_out:
            signals.append(s)
            name = s.backtrace[-1][0]
            signal_names.append("%s_%s" % (n, name))
            sig = CSRStatus(len(s), name=name)
            clr = CSR(name="%s_clr" % name)
            max = CSRStatus(len(s), name="%s_max" % name)
            min = CSRStatus(len(s), name="%s_min" % name)
            # setattr(c, sig.name, sig)
            setattr(c, clr.name, clr)
            setattr(c, max.name, max)
            setattr(c, min.name, min)
            c.comb += sig.status.eq(s)
            c.sync += If(clr.re | (max.status < s), max.status.eq(s))
            c.sync += If(clr.re | (min.status > s), min.status.eq(s))


    states = Cat(states)
    state = Signal(len(states))
    gpio.comb += state.eq(states)
    gpio.state = CSRStatus(len(state))
    gpio.state_clr = CSR()
    gpio.sync += [
        If(gpio.state_clr.re,
            gpio.state.status.eq(0),
        ).Else(
            gpio.state.status.eq(gpio.state.status | state),
        )
    ]

    # connect gpio output to "doi%i_en"
    for i, s in enumerate(gpio.o):
        csr = CSRStorage(len(state), name="do%i_en" % i)
        setattr(gpio, csr.name, csr)
        gpio.sync += s.eq((state & csr.storage) != 0)

    # connect state ins to "%s_en" and signal ins to "%s_sel"
    for n, c in chains:
        for s in c.state_in:
            csr = CSRStorage(len(state), name="%s_en" % s.backtrace[-1][0])
            setattr(c, csr.name, csr)
            c.sync += s.eq((state & csr.storage) != 0)

        for s in c.signal_in:
            csr = CSRStorage(bits_for(len(signals) - 1),
                             name="%s_sel" % s.backtrace[-1][0])
            setattr(c, csr.name, csr)
            c.sync += s.eq(signals[csr.storage])

    return state_names, signal_names
