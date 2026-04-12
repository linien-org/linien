import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

# helper to sign-extend a 14-bit value to Python int
def from_signed14(val):
    val = val & 0x3FFF
    if val & 0x2000:  # sign bit set
        val -= 0x4000
    return val

def to_14bit(val):
    return val & 0x3FFF

async def load_param(dut, addr, data):
    dut.en.value = 1
    dut.i_param_addr.value = addr
    dut.i_param_data.value = data
    await RisingEdge(dut.clk)
    dut.en.value = 0

async def reset(dut):
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.i_param_addr.value = 0
    dut.i_param_data.value = 0
    dut.i_active.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

async def run_ramp(dut, v_start, v_step, num_steps):
    """
    Loads params, activates block, collects output samples, deactivates.
    Returns list of observed v_drive values.
    """
    await load_param(dut, 0, to_14bit(v_start))
    await load_param(dut, 1, to_14bit(v_step))

    samples = []
    dut.i_active.value = 1

    for _ in range(num_steps):
        await RisingEdge(dut.clk)
        samples.append(from_signed14(dut.v_drive.value.integer))

    dut.i_active.value = 0
    await ClockCycles(dut.clk, 2)
    return samples

@cocotb.test()
async def test_basic_ramp_up(dut):
    """Simple positive ramp: start=0, step=+10"""
    cocotb.log.info("test_basic_ramp_up")
    clock = Clock(dut.clk, 8, units='ns')
    cocotb.start_soon(clock.start())
    await reset(dut)

    v_start, v_step, num_steps = 0, 10, 20
    samples = await run_ramp(dut, v_start, v_step, num_steps)

    # first sample should be v_start (active_pulse loads v_start)
    # each subsequent sample increments by v_step
    for i, s in enumerate(samples):
        expected = v_start + i * v_step
        assert s == expected, f"step {i}: expected {expected}, got {s}"
    cocotb.log.info(f"samples: {samples}")

@cocotb.test()
async def test_ramp_down(dut):
    """Negative step: start=100, step=-5"""
    cocotb.log.info("test_ramp_down")
    clock = Clock(dut.clk, 8, units='ns')
    cocotb.start_soon(clock.start())
    await reset(dut)

    v_start, v_step, num_steps = 100, -5, 20
    samples = await run_ramp(dut, v_start, v_step, num_steps)

    for i, s in enumerate(samples):
        expected = v_start + i * v_step
        assert s == expected, f"step {i}: expected {expected}, got {s}"
    cocotb.log.info(f"samples: {samples}")

@cocotb.test()
async def test_ramp_from_negative(dut):
    """Start from negative voltage, ramp up"""
    cocotb.log.info("test_ramp_from_negative")
    clock = Clock(dut.clk, 8, units='ns')
    cocotb.start_soon(clock.start())
    await reset(dut)

    v_start, v_step, num_steps = -500, 25, 20
    samples = await run_ramp(dut, v_start, v_step, num_steps)

    for i, s in enumerate(samples):
        expected = v_start + i * v_step
        assert s == expected, f"step {i}: expected {expected}, got {s}"
    cocotb.log.info(f"samples: {samples}")

@cocotb.test()
async def test_inactive_drives_zero(dut):
    """When i_active is low, v_drive should be 0"""
    cocotb.log.info("test_inactive_drives_zero")
    clock = Clock(dut.clk, 8, units='ns')
    cocotb.start_soon(clock.start())
    await reset(dut)

    await load_param(dut, 0, to_14bit(500))
    await load_param(dut, 1, to_14bit(10))

    # don't activate, just check output
    await ClockCycles(dut.clk, 5)
    assert from_signed14(dut.v_drive.value.integer) == 0, "v_drive should be 0 when inactive"

@cocotb.test()
async def test_two_sequential_ramps(dut):
    """Run two ramps back to back with different params, verify independence"""
    cocotb.log.info("test_two_sequential_ramps")
    clock = Clock(dut.clk, 8, units='ns')
    cocotb.start_soon(clock.start())
    await reset(dut)

    # first ramp
    samples1 = await run_ramp(dut, 0, 10, 10)
    for i, s in enumerate(samples1):
        assert s == i * 10, f"ramp1 step {i}: expected {i*10}, got {s}"

    # second ramp with different params
    samples2 = await run_ramp(dut, -100, 7, 10)
    for i, s in enumerate(samples2):
        expected = -100 + i * 7
        assert s == expected, f"ramp2 step {i}: expected {expected}, got {s}"

    cocotb.log.info("both ramps passed")
