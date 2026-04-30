from migen import *
from migen.fhdl.verilog import convert
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage

from ../regfile_adapter import RegFileAdapter
