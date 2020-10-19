#!/usr/bin/python3
# this code is based on redpid. See LICENSE for details.

from migen import *

from gateware.platform import Platform
from gateware.linien import RootModule
from bit2bin import bit2bin


def py_csrconstants(map, fil):
    fil.write("csr_constants = {\n")
    for k, v in root.linien.csrbanks.constants:
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
    root = RootModule(platform)

    fil = open("linien/server/csrmap.py", "w")
    py_csrconstants(root.linien.csrbanks.constants, fil)
    csr = get_csrmap(root.linien.csrbanks.banks)
    py_csrmap(csr, fil)
    fil.write("states = {}\n".format(repr(root.linien.state_names)))
    fil.write("signals = {}\n".format(repr(root.linien.signal_names)))
    fil.close()

    platform.add_source_dir("verilog")
    build_dir = 'fpga_build'
    platform.build(root, build_name="top", build_dir=build_dir)
    bit2bin("%s/top.bit" % build_dir, "%s/linien.bin" % build_dir, flip=True)
