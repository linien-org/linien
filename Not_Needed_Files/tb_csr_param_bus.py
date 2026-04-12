from migen import *
from Not_Needed_Files.csr_param_bus import (
    CSRParamBus, MAX_BLOCKS, PARAMS_PER_BLOCK,
    ADDR_BLOCK_TYPE, ADDR_DURATION,
    ADDR_PARAM_A, ADDR_PARAM_B, ADDR_PARAM_C, ADDR_PARAM_D,
)


def tb_csr_param_bus():
    dut = CSRParamBus()

    def run(dut):

        #helpers
        def write_param(block, addr, value):
            """write a single parameter: set up, pulse write, deassert."""
            yield dut.i_block_sel.eq(block)
            yield dut.i_param_addr.eq(addr)
            yield dut.i_param_data.eq(value)
            yield
            yield dut.i_param_write.eq(1)
            yield
            yield dut.i_param_write.eq(0)
            yield

        def read_block(block):
            """point the read mux at a block and return all params."""
            yield dut.i_read_block_sel.eq(block)
            yield  # one cycle for combinational settle
            return {
                "type": (yield dut.o_block_type),
                "dur":  (yield dut.o_duration),
                "a":    (yield dut.o_param_a),
                "b":    (yield dut.o_param_b),
                "c":    (yield dut.o_param_c),
                "d":    (yield dut.o_param_d),
            }

        def write_full_block(block, btype, duration, a, b, c, d):
            """write all 6 params for a block."""
            yield from write_param(block, ADDR_BLOCK_TYPE, btype)
            yield from write_param(block, ADDR_DURATION, duration)
            yield from write_param(block, ADDR_PARAM_A, a)
            yield from write_param(block, ADDR_PARAM_B, b)
            yield from write_param(block, ADDR_PARAM_C, c)
            yield from write_param(block, ADDR_PARAM_D, d)

        #test 1: write one param, read back
        print("test 1:  write one parameter, read back")
        yield from write_param(0, ADDR_PARAM_A, 12345)
        p = yield from read_block(0)
        assert p["a"] == 12345, f"FAIL: got {p['a']}"
        print("  passed")

        #test 2: write all 6 params, verify
        print("test 2:  write all 6 params for block 0")
        yield from write_full_block(0, 1, 50000, 2000, 10, 5000, 0)
        p = yield from read_block(0)
        assert p["type"] == 1, f"FAIL: type={p['type']}"
        assert p["dur"] == 50000, f"FAIL: dur={p['dur']}"
        assert p["a"] == 2000, f"FAIL: a={p['a']}"
        assert p["b"] == 10, f"FAIL: b={p['b']}"
        assert p["c"] == 5000, f"FAIL: c={p['c']}"
        assert p["d"] == 0, f"FAIL: d={p['d']}"
        print("  passed")

        #test 3: different blocks are isolated
        print("test 3:  write to block 5, block 0 unchanged")
        yield from write_full_block(5, 4, 100000, 8000, 2000, 500, 100)

        # re-read block 0 — should still have test 2 values
        p0 = yield from read_block(0)
        assert p0["type"] == 1
        assert p0["a"] == 2000

        # read block 5
        p5 = yield from read_block(5)
        assert p5["type"] == 4, f"FAIL: type={p5['type']}"
        assert p5["dur"] == 100000, f"FAIL: dur={p5['dur']}"
        assert p5["a"] == 8000, f"FAIL: a={p5['a']}"
        print("  passed")

        #test 4: block_type truncated to 3 bits
        print("test 4:  block_type is 3 bits (max 7)")
        yield from write_param(1, ADDR_BLOCK_TYPE, 0xFF)  # write 255
        p = yield from read_block(1)
        assert p["type"] == 7, f"FAIL: type={p['type']} (expected 7, 3-bit truncation of 0xFF)"
        print("  passed")

        #test 5: duration truncated to 24 bits
        print("test 5:  duration is 24 bits")
        yield from write_param(2, ADDR_DURATION, 0xFFFFFFFF)  # write max 32-bit
        p = yield from read_block(2)
        assert p["dur"] == 0xFFFFFF, f"FAIL: dur=0x{p['dur']:X} (expected 0xFFFFFF)"
        print("  passed")

        #test 6: switching read_block_sel updates combinationally
        print("test 6:  read mux switches combinationally")
        # block 0 has type=1 (ramp), block 5 has type=4 (chirp)
        yield dut.i_read_block_sel.eq(0)
        yield
        t0 = yield dut.o_block_type
        yield dut.i_read_block_sel.eq(5)
        yield
        t5 = yield dut.o_block_type
        assert t0 == 1, f"FAIL: block 0 type={t0}"
        assert t5 == 4, f"FAIL: block 5 type={t5}"
        print("  passed")

        #test 7: write to block 3 doesn't touch block 4
        print("test 7:  write isolation between adjacent blocks")
        yield from write_param(3, ADDR_PARAM_A, 9999)
        p3 = yield from read_block(3)
        p4 = yield from read_block(4)
        assert p3["a"] == 9999
        assert p4["a"] == 0, f"FAIL: block 4 param_a={p4['a']} (should be 0)"
        print("  passed")

        # ==== test 8: overwrite a parameter ====
        print("test 8:  overwrite param, verify new value")
        yield from write_param(0, ADDR_PARAM_A, 7777)
        p = yield from read_block(0)
        assert p["a"] == 7777, f"FAIL: a={p['a']}"
        print("  passed")

        #test 9: configure a ramp block, verify meanings
        print("test 9:  full ramp block config")
        # ramp: type=1, duration=12500 (100us), start=2000, step=10, target=5000
        yield from write_full_block(
            block=7,
            btype=1,        # ramp
            duration=12500,
            a=2000,         # start voltage
            b=10,           # step size per cycle
            c=5000,         # target voltage
            d=0,            # unused
        )
        p = yield from read_block(7)
        assert p["type"] == 1
        assert p["dur"] == 12500
        assert p["a"] == 2000   # start
        assert p["b"] == 10     # step
        assert p["c"] == 5000   # target
        print("  passed")

        #test 10: configure a chirp block, verify meanings
        print("test 10: full chirp block config")
        # chirp: type=4, duration=250000 (2ms), start_freq=5000, end_freq=2000,
        # amplitude=4000, dc_offset=1000
        yield from write_full_block(
            block=8,
            btype=4,          # chirp
            duration=250000,
            a=5000,           # start frequency
            b=2000,           # end frequency
            c=4000,           # amplitude
            d=1000,           # DC offset
        )
        p = yield from read_block(8)
        assert p["type"] == 4
        assert p["dur"] == 250000
        assert p["a"] == 5000   # start freq
        assert p["b"] == 2000   # end freq
        assert p["c"] == 4000   # amplitude
        assert p["d"] == 1000   # DC offset
        print("  passed")

        #test 11: num_blocks passthrough
        print("test 11: num_blocks passthrough")
        yield dut.i_num_blocks.eq(5)
        yield
        nb = yield dut.o_num_blocks
        assert nb == 5, f"FAIL: num_blocks={nb}"
        print("  passed")

        print("\nall 11 tests passed")

    run_simulation(dut, run(dut), vcd_name="csr_param_bus.vcd")


if __name__ == "__main__":
    tb_csr_param_bus()