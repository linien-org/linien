from migen.fhdl.std import *
from migen.bank.description import *
from migen.genlib.cdc import MultiReg

from .xadc import XADC
from .delta_sigma import DeltaSigmaCSR
from .dna import DNA


class Gpio(Module, AutoCSR):
    def __init__(self, pins):
        n = flen(pins)
        self._r_in = CSRStatus(n)
        self._r_out = CSRStorage(n)
        self._r_oe = CSRStorage(n)

        ###

        t = [TSTriple(1) for i in range(n)]
        self.specials += [ti.get_tristate(pins[i]) for i, ti in enumerate(t)]
        self.specials += MultiReg(Cat([ti.i for ti in t]), self._r_in.status)
        self.comb += [
                Cat([ti.o for ti in t]).eq(self._r_out.storage),
                Cat([ti.oe for ti in t]).eq(self._r_oe.storage),
        ]


class Slow(Module, AutoCSR):
    def __init__(self, exp, pwm, leds, xadc):
        self.submodules.gpio_n = Gpio(exp.n)
        self.submodules.gpio_p = Gpio(exp.p)

        self.submodules.deltasigma = DeltaSigmaCSR(pwm, out_cd="sys_double",
                width=16) # rc=1e-4, 2.6 LSB max peak-peak noise

        self.submodules.xadc = XADC(xadc)

        self.r_led = CSRStorage(flen(leds))
        self.comb += leds.eq(self.r_led.storage)

        self.submodules.dna = DNA()
