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

from migen.build.generic_platform import *
from migen.build.xilinx import XilinxPlatform

# https://github.com/RedPitaya/RedPitaya/blob/master/FPGA/release1/fpga/code/red_pitaya.xdc

_io = [
    ("user_led", i, Pins(p), IOStandard("LVCMOS33"),
     Drive(4), Misc("SLEW SLOW")) for i, p in enumerate(
        "F16 F17 G15 H15 K14 G14 J15 J14".split())
]

_io += [
    ("clk125", 0,
        Subsignal("p", Pins("U18")),
        Subsignal("n", Pins("U19")),
        IOStandard("DIFF_HSTL_I_18")
    ),
    ("adc", 0,
        Subsignal("clk", Pins("N20 P20"), Misc("SLEW FAST"), Misc("DRIVE 8")),
        Subsignal("cdcs", Pins("V18"), Misc("SLEW FAST"), Misc("DRIVE 8")),
        Subsignal("data_a", Pins("V17 U17 Y17 W16 Y16 W15 W14 Y14 "
                                 "W13 V12 V13 T14 T15 V15 T16 V16"),
                  ),  # Misc("IOB TRUE")),
        Subsignal("data_b", Pins("T17 R16 R18 P16 P18 N17 R19 T20 "
                                 "T19 U20 V20 W20 W19 Y19 W18 Y18"),
                  ),  # Misc("IOB TRUE")),
        IOStandard("LVCMOS18")  #, Drive(4)
    ),

    ("dac", 0,
        Subsignal("data", Pins("M19 M20 L19 L20 K19 J19 J20 H20 "
                               "G19 G20 F19 F20 D20 D19"),
                  Misc("SLEW SLOW"), Drive(4)),
        # Misc("IOB TRUE")
        Subsignal("wrt", Pins("M17"), Drive(8), Misc("SLEW FAST")),
        Subsignal("sel", Pins("N16"), Drive(8), Misc("SLEW FAST")),
        Subsignal("rst", Pins("N15"), Drive(8), Misc("SLEW FAST")),
        Subsignal("clk", Pins("M18"), Drive(8), Misc("SLEW FAST")),
        IOStandard("LVCMOS33")
    ),

    ("pwm", 0, Pins("T10"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),
    ("pwm", 1, Pins("T11"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),
    ("pwm", 2, Pins("P15"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),
    ("pwm", 3, Pins("U13"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),  # all IOB

    ("xadc", 0,
        Subsignal("p", Pins("C20 E17 B19 E18 K9")),
        Subsignal("n", Pins("B20 D18 A20 E19 L10")),
        IOStandard("LVCMOS33")
    ),

    ("exp", 0,
        Subsignal("p", Pins("G17 H16 J18 K17 L14 L16 K16 M14")),
        Subsignal("n", Pins("G18 H17 H18 K18 L15 L17 J16 M15")),
        IOStandard("LVCMOS33"),
    ),

    ("sata", 0,
        Subsignal("rx_p", Pins("T12")),
        Subsignal("rx_n", Pins("U12")),
        Subsignal("tx_p", Pins("U14")),
        Subsignal("tx_n", Pins("U15")),
        #IOStandard("DIFF_SSTL18_I")
    ),

    ("sata", 1,
        Subsignal("rx_p", Pins("P14")),
        Subsignal("rx_n", Pins("R14")),
        Subsignal("tx_p", Pins("N18")),
        Subsignal("tx_n", Pins("P19")),
        #IOStandard("DIFF_SSTL18_I")
    ),

    ("cpu", 0,
     Subsignal("mio", Pins("_ "*54)),
     Subsignal("ps_clk", Pins("_ "*1)),
     Subsignal("ps_porb", Pins("_ "*1)),
     Subsignal("ps_srstb", Pins("_ "*1)),
     Subsignal("ddr_vrn", Pins("_ "*1)),
     Subsignal("ddr_vrp", Pins("_ "*1)),
     Subsignal("DDR_addr", Pins("_ "*15)),
     Subsignal("DDR_ba", Pins("_ "*3)),
     Subsignal("DDR_cas_n", Pins("_ "*1)),
     Subsignal("DDR_ck_n", Pins("_ "*1)),
     Subsignal("DDR_ck_p", Pins("_ "*1)),
     Subsignal("DDR_cke", Pins("_ "*1)),
     Subsignal("DDR_cs_n", Pins("_ "*1)),
     Subsignal("DDR_dm", Pins("_ "*4)),
     Subsignal("DDR_dq", Pins("_ "*32)),
     Subsignal("DDR_dqs_n", Pins("_ "*4)),
     Subsignal("DDR_dqs_p", Pins("_ "*4)),
     Subsignal("DDR_odt", Pins("_ "*1)),
     Subsignal("DDR_ras_n", Pins("_ "*1)),
     Subsignal("DDR_reset_n", Pins("_ "*1)),
     Subsignal("DDR_we_n", Pins("_ "*1)),
    ),

]


class Platform(XilinxPlatform):
    default_clk_name = "clk125"
    default_clk_period = 8.

    def __init__(self):
        XilinxPlatform.__init__(self, "xc7z010-clg400-1", _io,
                                toolchain="vivado")
        self.toolchain.pre_synthesis_commands.append("read_xdc -ref processing_system7_v5_4_processing_system7 ../verilog/system_processing_system7_0_0.xdc")
        self.toolchain.with_phys_opt = True

    def do_finalize(self, fragment):
        try:
            clk125 = self.lookup_request("clk125")
            self.add_period_constraint(clk125.p, 8)
            self.add_platform_command(
                "set_clock_groups -asynchronous "
                "-group [get_clocks -include_generated_clocks {clk}] "
                "-group [get_clocks -include_generated_clocks clk_fpga_0]",
                clk=clk125.p)
            for i in range(2):
                try:
                    adc = self.lookup_request("adc", i)
                    #self.add_platform_command("set_input_delay "
                    #    "-clock {clk} 3.4 [get_ports {data}]",
                    #    clk=clk125, data=adc[0])
                except ConstraintError:
                    pass
        except ConstraintError:
            pass

        try:
            self.add_period_constraint(self.lookup_request("sata", 1).tx_p, 4)
        except ConstraintError:
            pass

        for r, obj in self.constraint_manager.matched:
            if r[0] == "cpu":
                for s in r[2:]:
                    for c in s.constraints:
                        if isinstance(c, Pins):
                            c.identifiers = []
