from migen import *
from migen.fhdl.verilog import convert
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from regfile_adapter import RegFileAdapter

m = RegFileAdapter()
convert(m).write("reg_file_adapter.v")
