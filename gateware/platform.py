# Robert Jordens <jordens@gmail.com> 2014

from mibuild.generic_platform import *
from mibuild.crg import SimpleCRG
from mibuild.xilinx_common import CRG_DS
from mibuild.xilinx_vivado import XilinxVivadoPlatform

_io = [
    ("clk125", 0,
        Subsignal("p", Pins("U18")),
        Subsignal("n", Pins("U19")),
        IOStandard("DIFF_HSTL_I_18")
    ),

    ("user_led", 0, Pins("F16"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),
    ("user_led", 1, Pins("F17"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),
    ("user_led", 2, Pins("G15"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),
    ("user_led", 3, Pins("H15"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),
    ("user_led", 4, Pins("K14"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),
    ("user_led", 5, Pins("G14"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),
    ("user_led", 6, Pins("J15"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),
    ("user_led", 7, Pins("J14"), IOStandard("LVCMOS33"),
            Drive(8), Misc("SLEW SLOW")),

    ("adc_clk", 0,
        Subsignal("clk", Pins("N20 P20"), IOStandard("LVCMOS18"),
            Drive(8)),
        Subsignal("cdcs", Pins("V18"), IOStandard("LVCMOS18"),
            Drive(8)),
        Misc("SLEW FAST")
    ),

    ("adc", 0, Pins("V17 U17 Y17 W16 Y16 W15 W14 Y14 "
        "W13 V12 V13 T14 T15 V15 T16 V16"),
        IOStandard("LVCMOS18")),

    ("adc", 1, Pins("T17 R16 R18 P16 P18 N17 R19 T20 "
        "T19 U20 V20 W20 W19 Y19 W18 Y18"),
        IOStandard("LVCMOS18")),

    ("dac_clk", 0, Pins("M18"), Drive(8), Misc("SLEW FAST")),

    ("dac", 0, 
        Subsignal("data", Pins("M19 M20 L19 L20 K19 J19 J20 H20 "
            "G19 G20 F19 F20 D20 D19"), Misc("SLEW SLOW"), Drive(4)),
        Subsignal("wrt", Pins("M17"), Drive(8), Misc("SLEW FAST")),
        Subsignal("sel", Pins("N16"), Drive(8), Misc("SLEW FAST")),
        Subsignal("rst", Pins("M18"), Drive(8), Misc("SLEW FAST")),
        IOStandard("LVCMOS33")
    ),

    ("dac_pwm", 0, Pins("T10"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),
    ("dac_pwm", 1, Pins("T11"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),
    ("dac_pwm", 2, Pins("P15"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),
    ("dac_pwm", 3, Pins("U13"), IOStandard("LVCMOS18"),
        Misc("DRIVE=12"), Misc("SLEW FAST")),

    ("xadc", 0,
        Subsignal("p", Pins("C20 E17 B19 E18 K9")),
        Subsignal("n", Pins("B20 D18 A20 E19 L10")),
        IOStandard("LVCMOS33")
    ),

    ("exp", 0,
        Subsignal("p0", Pins("G17"), Misc("PULLDOWN")),
        Subsignal("n0", Pins("G18"), Misc("PULLDOWN")),
        Subsignal("p1", Pins("H16")),
        Subsignal("n1", Pins("H17")),
        Subsignal("p2", Pins("J18")),
        Subsignal("n2", Pins("H18")),
        Subsignal("p3", Pins("K17")),
        Subsignal("n3", Pins("K18")),
        Subsignal("p4", Pins("L14")),
        Subsignal("n4", Pins("L15")),
        Subsignal("p5", Pins("L16")),
        Subsignal("n5", Pins("L17")),
        Subsignal("p6", Pins("K16")),
        Subsignal("n6", Pins("J16")),
        Subsignal("p7", Pins("M14"), Misc("PULLUP")),
        Subsignal("n7", Pins("M15"), Misc("PULLUP")),
        IOStandard("LVCMOS33"), Drive(8), Misc("SLEW FAST")
    ),

    ("sata", 0,
        Subsignal("rx_p", Pins("P14")),
        Subsignal("rx_n", Pins("R14")),
        Subsignal("tx_p", Pins("T12")),
        Subsignal("tx_n", Pins("U12")),
        IOStandard("DIFF_SSTL18_I")
    ),

    ("sata", 1,
        Subsignal("rx_p", Pins("N18")),
        Subsignal("rx_n", Pins("N19")),
        Subsignal("tx_p", Pins("U14")),
        Subsignal("tx_n", Pins("U15")),
        IOStandard("DIFF_SSTL18_I")
    ),
]


class Platform(XilinxVivadoPlatform):
    def __init__(self, ):
        XilinxVivadoPlatform.__init__(self, "xc7z010-clg400-1", _io,
                lambda p: CRG_DS(p, "clk125", None))

    def do_finalize(self, fragment):
        try:
            self.add_period_constraint(self.lookup_request("clk125").p, 8)
        except ConstrainError:
            pass
