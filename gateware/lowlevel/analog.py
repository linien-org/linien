# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

from migen import Cat, ClockSignal, Instance, Module, ResetSignal, Signal


class PitayaAnalog(Module):
    def __init__(self, adc, dac):
        self.comb += adc.cdcs.eq(1), adc.clk.eq(0b10)

        # sign = 1<<(len(dac.data) - 1)
        size = len(dac.data), True

        self.adc_a = Signal(size)
        self.adc_b = Signal(size)
        self.dac_a = Signal(size)
        self.dac_b = Signal(size)

        adca = Signal.like(adc.data_b)
        adcb = Signal.like(adc.data_a)
        self.sync += adca.eq(adc.data_a), adcb.eq(adc.data_b)
        # self.sync += self.adc_a.eq(-(sign ^ adca[2:])),
        # self.adc_b.eq(-(sign ^ adcb[2:]))
        self.comb += [
            # this is off by one LSB but otherwise min and max fail
            self.adc_a.eq(Cat(~adca[2:-1], adca[-1])),
            self.adc_b.eq(Cat(~adcb[2:-1], adcb[-1])),
        ]

        daca = Signal.like(dac.data)
        dacb = Signal.like(dac.data)
        # dacai, dacbi = Signal.like(dac.data), Signal.like(dac.data)
        # self.comb += dacai.eq(-self.dac_a), dacbi.eq(-self.dac_b)
        # self.sync += daca.eq(dacai ^ sign), dacb.eq(dacbi ^ sign)
        self.sync += [
            daca.eq(Cat(~self.dac_a[:-1], self.dac_a[-1])),
            dacb.eq(Cat(~self.dac_b[:-1], self.dac_b[-1])),
        ]

        self.comb += dac.rst.eq(ResetSignal("sys"))
        self.specials += [
            Instance(
                "ODDR",
                i_D1=0,
                i_D2=1,
                i_C=ClockSignal("sys_double"),
                o_Q=dac.clk,
                i_CE=1,
                i_R=0,
                i_S=0,
            ),
            Instance(
                "ODDR",
                i_D1=0,
                i_D2=1,
                i_C=ClockSignal("sys_double"),
                o_Q=dac.wrt,
                i_CE=1,
                i_R=0,
                i_S=0,
            ),
            Instance(
                "ODDR",
                i_D1=0,
                i_D2=1,
                i_C=ClockSignal("sys"),
                o_Q=dac.sel,
                i_CE=1,
                i_R=0,
                i_S=0,
            ),
            [
                Instance(
                    "ODDR",
                    i_D1=a,
                    i_D2=b,
                    i_C=ClockSignal("sys"),
                    o_Q=d,
                    i_CE=1,
                    i_R=0,
                    i_S=0,
                )
                for a, b, d in zip(daca, dacb, dac.data)
            ],
        ]
