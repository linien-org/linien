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

import copy
import json

from migen.fhdl.std import *
from migen.genlib.iir import IIR
from mibuild.tools import mkdir_noerror
from mibuild.generic_platform import *
from mibuild.xilinx_ise import XilinxISEPlatform, CRG_SE

class IIRImpl(Module):
	def __init__(self, name, **kwargs):
		self.name = name
		mkdir_noerror("build")
		json.dump(kwargs, open("build/{}.json".format(name), "w"))
		self.platform = platform = Platform()
		kwargs["order"] = 2
		x, y = [], []
		iir = [IIR(**kwargs) for i in range(6)]
		self.submodules += iir
		c = Signal((flen(iir[0].x), True))
		self.sync += c.eq(c + 1)
		do = platform.request("do")
		di = platform.request("di")
		y = Array([0, 1, c, di, c+di, c-di, di+c, di-c] + [iiri.y for iiri in iir])
		muxi = Signal(max=len(y))
		self.comb += do.eq(y[muxi])
		self.sync += muxi.eq(c)
		for i, iiri in enumerate(iir):
			muxi = Signal(max=len(y))
			self.sync += muxi.eq(c + i)
			self.sync += iiri.x.eq(y[muxi])
			self.sync += iiri.scale.eq(i*i - c - i)
			self.sync += iiri.a[1].eq(-4*c - 42341 + i)
			self.sync += iiri.a[2].eq(2*c + 33241 - i)
			self.sync += iiri.b[0].eq(8*c - 22323 + i)
			self.sync += iiri.b[1].eq(c + 34094 - i)
			self.sync += iiri.b[2].eq(4242-4*c + i)

	def build(self):
		self.platform.build(self, build_name=self.name)

class Platform(XilinxISEPlatform):
	xst_opt = """-ifmt MIXED
-opt_mode SPEED
-opt_level 2
-register_balancing yes"""
	ise_commands = """
trce -v 100 -fastpaths -o {build_name} {build_name}.ncd {build_name}.pcf
"""
	_io = {
		"spartan6": [
			("clk", 0, Pins("AB13")),
			("rst", 0, Pins("V5")),
			("do", 0,
				Pins("Y2 W3 W1 P8 P7 P6 P5 T4 T3",
					"U4 V3 N6 N7 M7 M8 R4 P4 M6 L6 P3"),
			),
			("di", 0,
				Pins("N4 M5 V2 V1 U3 U1 T2 T1 R3 R1 P2 P1"),
			),
		],
		"spartan3a": [
			("clk", 0, Pins("R7")),
			("rst", 0, Pins("R14")),
			("do", 0,
				Pins("K16 J16 C16 C15 E13 D14 D16 D15 "
				"E14 F13 G13 F14 E16 F15 H13 G14 "),
			),
			("di", 0,
				Pins("G16 F16 J12 J13 L14 L16 M15 M16 "
				"L13 K13 P16 N16 R15 P15 N13 N14"),
			),
		],}

	def __init__(self):
		io, chip = self._io["spartan3a"], "xc3s1400a-ft256-4"
		#io, chip = self._io["spartan6"], "xc6slx45-fgg484-2"
		XilinxISEPlatform.__init__(self, chip, io,
			lambda p: CRG_SE(p, "clk", "rst", 1000/32.))

if __name__ == "__main__":
	default = dict(width=18, saturate=True, form="tdf2")
	variations = dict(
			#form=["df1", "tdf2"],
			)

	name = "iir_baseline"
	IIRImpl(name, **default).build()

	for k, v in sorted(variations.items()):
		for vi in v:
			name = "iir_{}_{}".format(k, vi)
			kw = copy.copy(default)
			kw[k] = vi
			IIRImpl(name, **kw).build()
