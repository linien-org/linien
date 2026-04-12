# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
WAVES?=1
# FST ?= -fst # Use more efficient FST format # Doesn't seen to be working
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

SIM_BUILD				= sim_build/rtl
VERILOG_SOURCES += $(wildcard $(SRC_DIR)/*.sv)

# Allow sharing configuration between design and testbench via `include`:
VERILOG_INCLUDE_DIRS += $(SRC_DIR)

# Include the testbench sources:
VERILOG_SOURCES += $(wildcard *_tb.sv)
TOPLEVEL = $(basename $(wildcard *_tb.sv))

$(info TOPLEVEL=$(TOPLEVEL))

# List test modules to run, separated by commas and without the .py suffix:
COCOTB_TEST_MODULES = $(TOPLEVEL)

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

waves:
	gtkwave $(TOPLEVEL).vcd &
