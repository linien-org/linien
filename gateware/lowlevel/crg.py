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

from migen import ClockDomain, Instance, Module, Signal


class CRG(Module):
    def __init__(self, clk_adc, clk_ps, rst):
        self.clock_domains.cd_sys_quad = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys_double = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys_slow = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys_ps = ClockDomain()
        self.comb += [self.cd_sys_ps.clk.eq(clk_ps), self.cd_sys_ps.rst.eq(rst)]

        clk_adci = Signal()
        clk_adcb = Signal()
        clk = Signal(6)
        clkb = Signal(6)
        clk_fb = Signal()
        clk_fbb = Signal()
        locked = Signal()
        self.specials += [
            Instance("IBUFGDS", i_I=clk_adc.p, i_IB=clk_adc.n, o_O=clk_adci),
            Instance("BUFG", i_I=clk_adci, o_O=clk_adcb),
        ]
        self.specials += [
            Instance(
                "PLLE2_BASE",
                p_BANDWIDTH="OPTIMIZED",
                p_DIVCLK_DIVIDE=1,
                p_CLKFBOUT_PHASE=0.0,
                p_CLKFBOUT_MULT=8,
                p_CLKIN1_PERIOD=8.0,
                p_REF_JITTER1=0.01,
                p_STARTUP_WAIT="FALSE",
                i_CLKIN1=clk_adcb,
                i_PWRDWN=0,
                i_RST=rst,
                i_CLKFBIN=clk_fbb,
                o_CLKFBOUT=clk_fb,
                p_CLKOUT0_DIVIDE=2,
                p_CLKOUT0_PHASE=0.0,
                p_CLKOUT0_DUTY_CYCLE=0.5,
                o_CLKOUT0=clk[0],
                p_CLKOUT1_DIVIDE=4,
                p_CLKOUT1_PHASE=0.0,
                p_CLKOUT1_DUTY_CYCLE=0.5,
                o_CLKOUT1=clk[1],
                p_CLKOUT2_DIVIDE=8,
                p_CLKOUT2_PHASE=0.0,
                p_CLKOUT2_DUTY_CYCLE=0.5,
                o_CLKOUT2=clk[2],
                p_CLKOUT3_DIVIDE=120,
                p_CLKOUT3_PHASE=0.0,
                p_CLKOUT3_DUTY_CYCLE=0.5,
                o_CLKOUT3=clk[3],
                p_CLKOUT4_DIVIDE=4,
                p_CLKOUT4_PHASE=0.0,
                p_CLKOUT4_DUTY_CYCLE=0.5,
                o_CLKOUT4=clk[4],
                p_CLKOUT5_DIVIDE=4,
                p_CLKOUT5_PHASE=0.0,
                p_CLKOUT5_DUTY_CYCLE=0.5,
                o_CLKOUT5=clk[5],
                o_LOCKED=locked,
            )
        ]
        self.specials += Instance("BUFG", i_I=clk_fb, o_O=clk_fbb)
        for i, o, d in zip(
            clk,
            clkb,
            [self.cd_sys_quad, self.cd_sys_double, self.cd_sys, self.cd_sys_slow],
        ):
            self.specials += Instance("BUFG", i_I=i, o_O=d.clk)
        self.specials += Instance(
            "FD", p_INIT=1, i_D=~locked, i_C=self.cd_sys.clk, o_Q=self.cd_sys.rst
        )
