#!/usr/bin/python3
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

from migen import *

from gateware.platform import Platform
from gateware.redpid import RedPid
from bit2bin import bit2bin


def py_csrconstants(map, fil):
    fil.write("csr_constants = {\n")
    for k, v in redpid.pid.csrbanks.constants:
        fil.write("    '{}_{}': {},\n".format(k, v.name, v.value.value))
    fil.write("}\n\n")


def get_csrmap(banks):
    for name, csrs, map_addr, rmap in banks:
        reg_addr = 0
        for csr in csrs:
            yield [name, csr.name, map_addr, reg_addr, csr.size,
                   not hasattr(csr, "status")]
            reg_addr += (csr.size + 8 - 1)//8


def py_csrmap(it, fil):
    fil.write("csr = {\n")
    for reg in it:
        fil.write("    '{}_{}': ({}, 0x{:03x}, {}, {}),\n".format(*reg))
    fil.write("}\n")


if __name__ == "__main__":
    platform = Platform()
    redpid = RedPid(platform)

    fil = open("test/csrmap.py", "w")
    py_csrconstants(redpid.pid.csrbanks.constants, fil)
    csr = get_csrmap(redpid.pid.csrbanks.banks)
    py_csrmap(csr, fil)
    fil.write("states = {}\n".format(repr(redpid.pid.state_names)))
    fil.write("signals = {}\n".format(repr(redpid.pid.signal_names)))
    fil.close()

    platform.add_source_dir("verilog")
    platform.build(redpid, build_name="top")
    bit2bin("build/top.bit", "build/redpid.bin", flip=True)
