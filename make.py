#!/usr/bin/python3
# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *

from gateware.platform import Platform
from gateware.redpid import RedPid


def get_csrmap(banks):
    csr_base = 0x40300000
    for name, csrs, mapaddr, rmap in banks:
        reg_addr = csr_base + 0x800*mapaddr
        busword = flen(rmap.bus.dat_w)
        for csr in csrs:
            nr = (csr.size + busword - 1)//busword
            yield [name, csr.name, reg_addr, nr, not hasattr(csr, "status")]
            reg_addr += 4*nr


def py_csrmap(it, fil="test/csrmap.py"):
    csrmap = open(fil, "w")
    csrmap.write("csrmap = {\n")
    for reg in it:
        csrmap.write("    '{}_{}': (0x{:08x}, {}, {}),\n".format(*reg))
    csrmap.write("}\n")


if __name__ == "__main__":
    platform = Platform()
    redpid = RedPid(platform)
    py_csrmap(get_csrmap(redpid.csrbanks.banks))
    platform.add_source_dir("verilog")
    platform.build_cmdline(redpid, build_name="redpid")
