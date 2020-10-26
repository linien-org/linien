from migen import *
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus, CSR

from .iir import Iir
from .pid import PID
from .limit import LimitCSR
from .modulate import Modulate, Demodulate


class FastChain(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25, coeff_width=18, mod=None, offset_signal=None):
        self.adc = Signal((width, True))
        self.dac = Signal((signal_width, True))

        self.y_tap = CSRStorage(2)
        self.invert = CSRStorage(1)

        x_hold = Signal()
        x_clear = Signal()
        x_railed = Signal()
        y_hold = Signal()
        y_clear = Signal()
        y_sat = Signal()
        y_railed = Signal()

        self.state_in = x_hold, x_clear, y_hold, y_clear
        self.state_out = x_railed, y_sat, y_railed

        x = Signal((signal_width, True))
        dx = Signal((signal_width, True))
        y = Signal((signal_width, True))
        dy = Signal((signal_width, True))
        rx = Signal((signal_width, True))

        self.signal_in = dx, dy, rx
        self.signal_out = x, y

        ###

        self.submodules.demod = Demodulate(width=width)
        self.submodules.x_limit = LimitCSR(width=signal_width, guard=1)
        self.submodules.iir_c = Iir(
            width=signal_width, coeff_width=coeff_width, shift=coeff_width-2,
            order=1)
        self.submodules.iir_d = Iir(
            width=signal_width, coeff_width=coeff_width, shift=coeff_width-2,
            order=2)

        if mod is None:
            self.submodules.mod = Modulate(width=width)
            mod = self.mod

        self.submodules.y_limit = LimitCSR(width=signal_width, guard=3)

        ###

        s = signal_width - width

        self.comb += [
            self.demod.x.eq(self.adc),
            self.demod.phase.eq(mod.phase),
            self.x_limit.x.eq((self.demod.y << s) + dx),
            x_railed.eq(self.x_limit.error),

            self.iir_c.x.eq(self.x_limit.y),
            self.iir_c.hold.eq(y_hold),
            self.iir_c.clear.eq(y_clear),

            self.iir_d.x.eq(self.iir_c.y),
            self.iir_d.hold.eq(y_hold),
            self.iir_d.clear.eq(y_clear),

            y_sat.eq(
                (self.iir_c.error & (self.y_tap.storage > 1)) |
                (self.iir_d.error & (self.y_tap.storage > 2))
            ),
        ]
        ya = Signal((width + 3, True))
        ys = Array([self.iir_c.x, self.iir_c.y,
                    self.iir_d.y])

        self.sync += ya.eq(((dy >> s))),
        self.comb += [
            self.y_limit.x.eq(
                Mux(self.invert.storage, -1, 1) * (
                    ys[self.y_tap.storage] + (ya << s) + (offset_signal << s)
                )
            ),
            y.eq(self.y_limit.y),
            y_railed.eq(self.y_limit.error),

            self.dac.eq(self.y_limit.y)
        ]


class SlowChain(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25):
        s = signal_width - width

        self.input = Signal((width, True))
        self.output = Signal((width, True))

        out = Signal((signal_width, True))

        self.state_in = []
        self.state_out = []
        self.signal_in = []
        self.signal_out = [out]

        self.submodules.pid = PID()
        self.submodules.limit = LimitCSR(width=width, guard=5)

        self.comb += [
            self.pid.input.eq(self.input),
            self.output.eq(self.pid.pid_out),

            out.eq(self.limit.y << s)
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
