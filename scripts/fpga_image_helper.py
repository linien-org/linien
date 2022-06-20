# Copyright 2014-2015 Robert Jördens <jordens@gmail.com>
# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
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

# this file compiles the FPGA image. You shouldn't call it directly though but
# use `build_fpga_image.sh`
import sys
from pathlib import Path

REPO_ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT_DIR))  # need to explicitly cast to string

from bit2bin import bit2bin

from gateware.linien import RootModule
from gateware.platform import Platform


def py_csrconstants(map, fil):
    fil.write("csr_constants = {\n")
    for k, v in root.linien.csrbanks.constants:
        fil.write("    '{}_{}': {},\n".format(k, v.name, v.value.value))
    fil.write("}\n\n")


def get_csrmap(banks):
    for name, csrs, map_addr, rmap in banks:
        reg_addr = 0
        for csr in csrs:
            yield [
                name,
                csr.name,
                map_addr,
                reg_addr,
                csr.size,
                not hasattr(csr, "status"),
            ]
            reg_addr += (csr.size + 8 - 1) // 8


def py_csrmap(it, fil):
    fil.write("csr = {\n")
    for reg in it:
        fil.write("    '{}_{}': ({}, 0x{:03x}, {}, {}),\n".format(*reg))
    fil.write("}\n")


if __name__ == "__main__":
    platform = Platform()
    root = RootModule(platform)

    with open(
        REPO_ROOT_DIR / "linien-server" / "linien_server" / "csrmap.py", "w"
    ) as fil:
        py_csrconstants(root.linien.csrbanks.constants, fil)
        csr = get_csrmap(root.linien.csrbanks.banks)
        py_csrmap(csr, fil)
        fil.write("states = {}\n".format(repr(root.linien.state_names)))
        fil.write("signals = {}\n".format(repr(root.linien.signal_names)))

    platform.add_source_dir(REPO_ROOT_DIR / "gateware" / "verilog")
    build_dir = REPO_ROOT_DIR / "fpga_build"
    platform.build(root, build_name="top", build_dir=build_dir)
    bit2bin(
        build_dir / "top.bit",
        REPO_ROOT_DIR / "linien-server" / "linien_server" / "linien.bin",
        flip=True,
    )
