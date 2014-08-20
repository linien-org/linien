# Robert Jordens <jordens@gmail.com> 2014

from collections import OrderedDict

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *
from migen.fhdl.bitcontainer import bits_for
from migen.genlib.cordic import Cordic

from .iir import Iir
from .limit import Limit


signal_width = 25
coeff_width = 18

ports_layout = [
        ("i", (signal_width, True)),
        ("o", (signal_width, True)),
]


class Sweep(Module):
    def __init__(self):
        self.o = Signal((signal_width, True))


class InOut(Module, AutoCSR):
    def __init__(self, i, o):
        self.ports = Record(ports_layout)

        self._in_min = CSRStorage(signal_width)
        self._in_max = CSRStorage(signal_width)
        self._in_shift = CSRStorage(signal_width)
        self._in_val = CSRStatus(signal_width)
        self._in_low = CSRStatus()
        self._in_high = CSRStatus()

        self._demod = CSRStorage()
        self._demod_amp = CSRStorage(signal_width)
        self._demod_phase = CSRStorage(signal_width)

        self._mod = CSRStorage()
        self._mod_amp = CSRStorage(signal_width)
        self._mod_freq = CSRStorage(32)

        self._sweep = CSRStorage()
        self._sweep_amp = CSRStorage(signal_width)
        self._sweep_offset = CSRStorage(signal_width)
        self._sweep_freq = CSRStorage(signal_width)

        self._out_min = CSRStorage(signal_width)
        self._out_max = CSRStorage(signal_width)
        self._out_shift = CSRStorage(signal_width)
        self._out_val = CSRStatus(signal_width)
        self._out_low = CSRStatus()
        self._out_high = CSRStatus()

        ###

        #self.submodules.mod = Cordic(width=signal_width, guard=None)
        #self.submodules.demod = Cordic(width=signal_width, guard=None)
        self.submodules.sweep = Sweep()
        self.submodules.limit = Limit()
        mod_phase = Signal(32)
        demod_phase = Signal(32)

        self.sync += [
                mod_phase.eq(mod_phase + self._mod_freq.storage),
                demod_phase.eq(mod_phase + self._demod_phase.storage),
        ]

        self.comb += [
                #self.mod.xi.eq(self._mod_amp.storage),
                #self.mod.zi.eq(mod_phase),
                #self.demod.xi.eq(i),
                #self.demod.zi.eq(demod_phase),
                #self.ports.o.eq(Mux(self._demod.storage, self.demod.xo, i)),
                self.ports.o.eq(i),
                self.limit.x.eq(self.ports.i
                    #+ Mux(self._mod.storage, self.mod.xo, 0)
                    #+ Mux(self._sweep.storage, self.sweep.o, 0)
                ),
                o.eq(self.limit.y),
        ]


class IIR1(Module, AutoCSR):
    def __init__(self):
        self.ports = Record(ports_layout)
        self.submodules.m = Iir(signal_width=flen(self.ports.i), coeff_width=coeff_width,
                order=1)
        self.comb += self.ports.o.eq(self.m.y), self.m.x.eq(self.ports.i)


class IIR2(Module, AutoCSR):
    def __init__(self):
        self.ports = Record(ports_layout)
        self.submodules.m = Iir(signal_width=flen(self.ports.i), coeff_width=coeff_width,
                order=2)
        self.comb += self.ports.o.eq(self.m.y), self.m.x.eq(self.ports.i)


class FilterMux(Module, AutoCSR):
    def __init__(self, parts):
        outs = Array([part.ports.o for part in parts])

        for i, part in enumerate(parts):
            m = CSRStorage(bits_for(len(parts)))
            setattr(self, "_mux%i" % i, m)
            mr = Signal.like(m.storage)
            self.sync += mr.eq(m.storage), part.ports.i.eq(outs[mr])


class Pid(Module, AutoCSR):
    def __init__(self):
        self.r_version = CSRStatus(8)
        self.r_version.status.reset = 1

        self.ins = [Signal((14, True)) for i in range(2)]
        self.outs = [Signal((14, True)) for i in range(2)]
        parts = OrderedDict([
                ("io_a", InOut(self.ins[0], self.outs[0])),
                ("io_b", InOut(self.ins[1], self.outs[1])), 
                ("iir1_a", IIR1()),
                #iir1_b=IIR1(), iir1_c=IIR1(), iir1_d=IIR1(),
                #iir2_a=IIR2(), iir2_b=IIR2(), iir2_c=IIR2(), iir2_d=IIR2(),
        ])
        self.submodules.mux = FilterMux(parts.values())
        for i, (k, v) in enumerate(parts.items()):
            setattr(self.submodules, k, v)
