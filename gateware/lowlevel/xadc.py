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

from migen import (
    Case,
    Cat,
    ClockSignal,
    If,
    Instance,
    Module,
    Replicate,
    ResetSignal,
    Signal,
)
from misoc.interconnect.csr import AutoCSR, CSRStatus


class XADC(Module, AutoCSR):
    def __init__(self, xadc):
        self.alarm = Signal(8)
        self.ot = Signal()
        self.adc = [Signal((12, True)) for i in range(4)]

        self.temp = CSRStatus(12)
        self.v = CSRStatus(12)
        self.a = CSRStatus(12)
        self.b = CSRStatus(12)
        self.c = CSRStatus(12)
        self.d = CSRStatus(12)

        ###

        self.comb += [
            self.adc[0].eq(self.a.status),
            self.adc[1].eq(self.b.status),
            self.adc[2].eq(self.c.status),
            self.adc[3].eq(self.d.status),
        ]

        busy = Signal()
        channel = Signal(7)
        eoc = Signal()
        eos = Signal()
        data = Signal(16)
        drdy = Signal()

        vin = Cat(xadc.n[:2], Replicate(0, 6), xadc.n[2:4], Replicate(0, 6), xadc.n[4])
        vip = Cat(xadc.p[:2], Replicate(0, 6), xadc.p[2:4], Replicate(0, 6), xadc.p[4])
        self.specials += Instance(
            "XADC",
            p_INIT_40=0x0000,
            p_INIT_41=0x2F0F,
            p_INIT_42=0x0400,  # config
            p_INIT_48=0x0900,
            p_INIT_49=0x0303,  # channels VpVn, Temp
            p_INIT_4A=0x47E0,
            p_INIT_4B=0x0000,  # avg VpVn, temp
            p_INIT_4C=0x0800,
            p_INIT_4D=0x0303,  # bipolar
            p_INIT_4E=0x0000,
            p_INIT_4F=0x0000,  # acq time
            p_INIT_50=0xB5ED,
            p_INIT_51=0x57E4,  # temp trigger, vccint upper alarms
            p_INIT_52=0xA147,
            p_INIT_53=0xCA33,  # vccaux upper, temp over upper
            p_INIT_54=0xA93A,
            p_INIT_55=0x52C6,  # temp reset, vccint lower
            p_INIT_56=0x9555,
            p_INIT_57=0xAE4E,  # vccaux lower, temp over reset
            p_INIT_58=0x5999,
            p_INIT_5C=0x5111,  # vbram uppper, vbram lower
            p_INIT_59=0x5555,
            p_INIT_5D=0x5111,  # vccpint upper lower
            p_INIT_5A=0x9999,
            p_INIT_5E=0x91EB,  # vccpaux upper lower
            p_INIT_5B=0x6AAA,
            p_INIT_5F=0x6666,  # vccdro upper lower
            o_ALM=self.alarm,
            o_OT=self.ot,
            o_BUSY=busy,
            o_CHANNEL=channel,
            o_EOC=eoc,
            o_EOS=eos,
            i_VAUXN=vin[:16],
            i_VAUXP=vip[:16],
            i_VN=vin[16],
            i_VP=vip[16],
            i_CONVST=0,
            i_CONVSTCLK=0,
            i_RESET=ResetSignal(),
            o_DO=data,
            o_DRDY=drdy,
            i_DADDR=channel,
            i_DCLK=ClockSignal(),
            i_DEN=eoc,
            i_DI=0,
            i_DWE=0,
            # o_JTAGBUSY=, o_JTAGLOCKED=, o_JTAGMODIFIED=, o_MUXADDR=,
        )

        channels = {
            0: self.temp,
            3: self.v,
            16: self.b,
            17: self.c,
            24: self.a,
            25: self.d,
        }

        self.sync += [
            If(
                drdy,
                Case(
                    channel,
                    dict((k, v.status.eq(data >> 4)) for k, v in channels.items()),
                ),
            )
        ]
