#!/usr/bin/python3
# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *

from gateware.platform import Platform
from gateware.redpid import RedPid


if __name__ == "__main__":
    platform = Platform()
    redpid = RedPid(platform)

    csr_base = 0x40300000
    for name, csrs, mapaddr, rmap in redpid.csrbanks.banks:
        reg_base = csr_base + 0x800*mapaddr
        busword = flen(rmap.bus.dat_w)
        for csr in csrs:
            nr = (csr.size + busword - 1)//busword
            r = "{}_{},0x{:08x},{},{}".format(name, csr.name, reg_base, nr,
                    "ro" if hasattr(csr, "status") else "rw")
            print(r)
            reg_base += 4*nr

    platform.add_source_dir("verilog")
    platform.build_cmdline(redpid, build_name="redpid")
