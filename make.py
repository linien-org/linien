#!/usr/bin/python3
# (C) Roberr Jordens <jordens@gmail.com> 2014, 2015

from migen.fhdl.std import *

from gateware.platform import Platform
from gateware.redpid import RedPid
from bit2bin import bit2bin

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
    csr = get_csrmap(redpid.pid.csrbanks.banks)
    py_csrmap(csr, fil)
    fil.write("states = {}\n".format(repr(redpid.pid.state_names)))
    fil.write("signals = {}\n".format(repr(redpid.pid.signal_names)))
    fil.close()

    platform.add_source_dir("verilog")
    platform.build_cmdline(redpid, build_name="redpid")
    bit2bin("build/redpid.bit", "build/redpid.bin", flip=True)
