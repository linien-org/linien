from migen import Signal, Module, Array, Mux, Cat, If, bits_for
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus, CSR

from .iir import Iir
from .pid import PID
from .limit import LimitCSR
from .modulate import Demodulate


class FastChain(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25, coeff_width=18, mod=None, offset_signal=None):
        self.adc = Signal((width, True))
        # output of in-phase demodulated signal
        self.out_i = Signal((signal_width, True))
        # output of quadrature demodulated signal
        self.out_q = Signal((signal_width, True))

        self.y_tap = CSRStorage(2)
        self.invert = CSRStorage(1)

        self.state_in = []
        self.state_out = []

        x = Signal((signal_width, True))
        dx = Signal((signal_width, True))
        dy = Signal((signal_width, True))

        self.signal_in = dx, dy
        self.signal_out = x, self.out_i, self.out_q

        ###

        self.submodules.demod = Demodulate(width=width)

        ###

        s = signal_width - width

        self.comb += [
            self.demod.x.eq(self.adc),
            self.demod.phase.eq(mod.phase),
        ]
        ya = Signal((width + 3, True))
        self.sync += ya.eq(((dy >> s))),


        ###

        def init_submodule(name, submodule):
            setattr(self.submodules, name, submodule)

        # iterate over in-phase and quadrature signal
        # both have filters and limits
        for sub_channel_idx in (0, 1):
            x_limit = LimitCSR(width=signal_width, guard=1)
            init_submodule('x_limit_%d' % (sub_channel_idx + 1), x_limit)
            iir_c = Iir(
                width=signal_width, coeff_width=coeff_width, shift=coeff_width-2,
                order=1
            )
            init_submodule('iir_c_%d' % (sub_channel_idx + 1), iir_c)
            iir_d = Iir(
                width=signal_width, coeff_width=coeff_width, shift=coeff_width-2,
                order=2
            )
            init_submodule('iir_d_%d' % (sub_channel_idx + 1), iir_d)
            y_limit = LimitCSR(width=signal_width, guard=3)
            init_submodule('y_limit_%d' % (sub_channel_idx + 1), y_limit)


            self.comb += [
                x_limit.x.eq(([self.demod.i, self.demod.q][sub_channel_idx] << s) + dx),

                iir_c.x.eq(x_limit.y),
                iir_c.hold.eq(0),
                iir_c.clear.eq(0),

                iir_d.x.eq(iir_c.y),
                iir_d.hold.eq(0),
                iir_d.clear.eq(0),
            ]

            ys = Array([iir_c.x, iir_c.y, iir_d.y])

            self.comb += [
                y_limit.x.eq(
                    Mux(self.invert.storage, -1, 1) * (
                        ys[self.y_tap.storage] + (ya << s) + (offset_signal << s)
                    )
                ),

                (
                    self.out_i,
                    self.out_q
                )[sub_channel_idx].eq(y_limit.y)
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
