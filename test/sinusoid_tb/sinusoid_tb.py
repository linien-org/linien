import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import Timer
from cocotb.triggers import First


# method to load in values into the DUT.
async def load(dut, address, data):
    dut.i_param_addr.value = address
    dut.i_param_data.value = data
    dut.i_en.value = 1
    await RisingEdge(dut.clk)

    # after rising edge, de-assert
    dut.i_en.value = 0


async def rand_load_and_run(dut):
    # set initial conditions
    dut.i_active.value = 0
    dut.i_en.value = 0
    await ClockCycles(dut.clk, 3)

    # sequentially load in value
    await load(dut, 0, random.randint(-8192, 8191))
    await load(dut, 1, random.randint(0, 8191))
    await load(dut, 2, random.randint(-8192, 0))
    await load(dut, 3, random.randint(0, 8191))
    await load(
        dut,
        4,
        random.randint(int((1 / 125e6) * (2**32)), int((10000 / 125e6) * (2**32))),
    )

    # after loading all the values, set enable back to low an activate it for some
    # amount of time
    dut.i_active.value = 1

    await ClockCycles(dut.clk, 100000)


@cocotb.test()
async def test1(dut):
    cocotb.log.info("test 1")
    dut.rst_n.value = 0
    dut.i_en.value = 0
    dut.i_active.value = 0
    # clock period should be 8ns, equivalent to 125 mHz
    clock = Clock(dut.clk, 8, unit="ns")

    start_clock = cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    await rand_load_and_run(dut)
    await rand_load_and_run(dut)
    await rand_load_and_run(dut)
    await rand_load_and_run(dut)
