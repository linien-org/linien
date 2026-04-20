from migen import *
from migen.fhdl.verilog import convert
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from ../regfile_adapter import RegFileAdapter
