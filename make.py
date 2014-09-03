#!/usr/bin/python3
# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *

from gateware.platform import Platform
from gateware.redpid import RedPid
from bit2bin import bit2bin

def get_csrmap(banks):
    csr_base = 0x40300000
    for name, csrs, mapaddr, rmap in banks:
        reg_addr = csr_base + 0x800*mapaddr
        for csr in csrs:
            yield [name, csr.name, reg_addr, csr.size, not hasattr(csr, "status")]
            reg_addr += 4*((csr.size + 8 - 1)//8)


def py_csrmap(it, fil):
    fil.write("csr = {\n")
    for reg in it:
        fil.write("    '{}_{}': (0x{:08x}, {}, {}),\n".format(*reg))
    fil.write("}\n")


if __name__ == "__main__":
    platform = Platform()
    redpid = RedPid(platform)
    platform.add_source_dir("verilog")
    platform.build_cmdline(redpid, build_name="redpid")
    bit2bin("build/redpid.bit", "build/redpid.bin", flip=True)

    fil = open("test/csrmap.py", "w")
    csr = get_csrmap(redpid.pid.csrbanks.banks)
    py_csrmap(csr, fil)
    fil.write("states = {}\n".format(repr(redpid.pid.state_names)))
    fil.write("signals = {}\n".format(repr(redpid.pid.signal_names)))
    fil.close()
