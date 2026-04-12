import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
import random

def to_14bit(val):
    return val & 0x3FFF

def from_signed14(val):
    val = val & 0x3FFF
    if val & 0x2000:
        val -= 0x4000
    return val

@cocotb.test()
async def test_simple(dut):
    clock = Clock(dut.clk, 8, units='ns')
    cocotb.start_soon(clock.start())

    # init
    dut.rst_n.value = 0
    dut.i_en.value = 0
    dut.i_active.value = 0
    dut.i_param_addr.value = 0
    dut.i_param_data.value = 0
    dut.i_wr_en.value = 0
    dut.i_wr_addr.value = 0
    dut.i_wr_data.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 4)

    # load 16 simple values into BRAM: 0, 100, 200, ... 1500
    cocotb.log.info("loading BRAM...")
    for i in range(1024):
        dut.i_wr_addr.value = i
        val=random.randint(-12000,12000)
        dut.i_wr_data.value = to_14bit(val)
        dut.i_wr_en.value = 1
        await RisingEdge(dut.clk)
    dut.i_wr_en.value = 0
    await ClockCycles(dut.clk, 4)

    # load clk_div = 1
    cocotb.log.info("loading clk_div...")
    dut.i_en.value = 1
    dut.i_param_addr.value = 0
    div=20
    dut.i_param_data.value = div
    await RisingEdge(dut.clk)
    dut.i_en.value = 0
    await ClockCycles(dut.clk, 4)

    # activate and just watch for 30 cycles
    cocotb.log.info("activating...")
    dut.i_active.value = 1
    for i in range(1024*div):
        await RisingEdge(dut.clk)
        #cocotb.log.info(
            #f"cycle {i}: bram_addr={dut.o_bram_addr.value}, "
            #f"o_drive={from_signed14(dut.o_drive.value)}"
        #)
    dut.i_active.value = 0
    await ClockCycles(dut.clk, 200)
    cocotb.log.info("done")
