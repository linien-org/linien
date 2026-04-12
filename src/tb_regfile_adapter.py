from migen import *
from regfile_adapter import RegFileAdapter


def tb_regfile_adapter():
    dut = RegFileAdapter()

    def run(dut):

        # helpers
        def wait(n):
            for _ in range(n):
                yield

        def do_write(addr, data):
            """full write transaction: set addr+data, pulse strobe, wait."""
            yield dut.wr_addr.storage.eq(addr)
            yield dut.wr_data.storage.eq(data)
            yield
            yield dut.wr_strobe.storage.eq(1)
            yield
            yield dut.wr_strobe.storage.eq(0)
            yield

        # test 1: outputs idle at zero
        print("test 1:  outputs default to zero")
        yield
        assert (yield dut.o_wr_en) == 0
        assert (yield dut.o_wr_addr) == 0
        assert (yield dut.o_wr_data) == 0
        assert (yield dut.o_num_blocks) == 0
        assert (yield dut.o_enable) == 0
        print("passed")

        # test 2: addr and data pass through combinationally
        print("test 2:  addr and data passthrough")
        yield dut.wr_addr.storage.eq(0x2A)
        yield dut.wr_data.storage.eq(0xDEADBEEF)
        yield
        assert (yield dut.o_wr_addr) == 0x2A
        assert (yield dut.o_wr_data) == 0xDEADBEEF
        assert (yield dut.o_wr_en) == 0, "wr_en should still be 0 (no strobe yet)"
        print("passed")

        # test 3: strobe generates single-cycle pulse
        print("test 3:  strobe rising edge generates 1-cycle wr_en pulse")
        yield dut.wr_strobe.storage.eq(1)
        yield
        # first cycle after 0 to 1: pulse should be high
        en = yield dut.o_wr_en
        assert en == 1, f"FAIL: wr_en={en} (expected 1 on rising edge)"
        yield
        # second cycle with strobe still high: pulse should be gone
        en = yield dut.o_wr_en
        assert en == 0, f"FAIL: wr_en={en} (expected 0, strobe held high)"
        yield dut.wr_strobe.storage.eq(0)
        yield
        print("passed")

        # test 4: strobe held high doesn't re-fire
        print("test 4:  strobe held high doesn't produce extra pulses")
        yield dut.wr_strobe.storage.eq(1)
        yield  # rising edge cycle
        yield  # strobe still high
        yield
        yield
        # only the first cycle should have pulsed
        en = yield dut.o_wr_en
        assert en == 0
        yield dut.wr_strobe.storage.eq(0)
        yield
        print("passed")

        # test 5: second write transaction works
        print("test 5:  second transaction after clearing strobe")
        yield from do_write(0x10, 0x12345678)
        # during the strobe cycle, addr/data should have been correct
        # check that wr_en is back to 0 now
        en = yield dut.o_wr_en
        assert en == 0
        addr = yield dut.o_wr_addr
        assert addr == 0x10, f"FAIL: addr=0x{addr:02X}"
        data = yield dut.o_wr_data
        assert data == 0x12345678, f"FAIL: data=0x{data:08X}"
        print("passed")

        # test 6: num_blocks passthrough
        print("test 6:  num_blocks passthrough")
        yield dut.num_blocks.storage.eq(7)
        yield
        nb = yield dut.o_num_blocks
        assert nb == 7, f"FAIL: num_blocks={nb}"
        print("passed")

        # test 7: num_blocks truncated to 4 bits
        print("test 7:  num_blocks truncated to 4 bits (max 15)")
        yield dut.num_blocks.storage.eq(0xF)
        yield
        nb = yield dut.o_num_blocks
        assert nb == 15, f"FAIL: num_blocks={nb}"
        print("passed")

        # test 8: enable passthrough
        print("test 8:  enable passthrough")
        yield dut.enable.storage.eq(1)
        yield
        en = yield dut.o_enable
        assert en == 1, f"FAIL: enable={en}"
        yield dut.enable.storage.eq(0)
        yield
        en = yield dut.o_enable
        assert en == 0, f"FAIL: enable={en}"
        print("passed")

        # test 9: rapid back-to-back writes
        print("test 9:  rapid back-to-back writes (two separate strobes)")
        # first write
        yield dut.wr_addr.storage.eq(0x00)
        yield dut.wr_data.storage.eq(1111)
        yield dut.wr_strobe.storage.eq(1)
        yield
        en1 = yield dut.o_wr_en
        assert en1 == 1, "first write pulse missing"
        # clear strobe
        yield dut.wr_strobe.storage.eq(0)
        yield
        # second write
        yield dut.wr_addr.storage.eq(0x08)
        yield dut.wr_data.storage.eq(2222)
        yield dut.wr_strobe.storage.eq(1)
        yield
        en2 = yield dut.o_wr_en
        assert en2 == 1, "second write pulse missing"
        addr2 = yield dut.o_wr_addr
        data2 = yield dut.o_wr_data
        assert addr2 == 0x08, f"FAIL: addr=0x{addr2:02X}"
        assert data2 == 2222, f"FAIL: data={data2}"
        yield dut.wr_strobe.storage.eq(0)
        yield
        print("passed")

        # test 10: write full block 0 sequence (type + 3 params)
        print("test 10: simulate full block 0 config (ramp: type=1, 3 params)")
        # slot 0 base = 0x00
        yield from do_write(0x00, 1)       # block type = ramp
        yield from do_write(0x01, 2000)    # param 0: v_start
        yield from do_write(0x02, 10)      # param 1: step_size
        yield from do_write(0x03, 12500)   # param 2: duration
        # verify addr/data reflect last write
        addr = yield dut.o_wr_addr
        data = yield dut.o_wr_data
        assert addr == 0x03
        assert data == 12500
        print("passed")

        # test 11: write to block 5 (base = 0x28)
        print("test 11: simulate block 5 config (base addr 0x28)")
        yield from do_write(0x28, 4)       # block type = sinusoid
        yield from do_write(0x29, 500)     # param 0: v_mid
        addr = yield dut.o_wr_addr
        assert addr == 0x29, f"FAIL: addr=0x{addr:02X}"
        print("passed")

        # test 12: enable and num_blocks independent of write bus
        print("test 12: enable and num_blocks don't interfere with writes")
        yield dut.enable.storage.eq(1)
        yield dut.num_blocks.storage.eq(5)
        yield from do_write(0x40, 0xCAFE)
        en = yield dut.o_enable
        nb = yield dut.o_num_blocks
        assert en == 1, f"FAIL: enable={en}"
        assert nb == 5, f"FAIL: num_blocks={nb}"
        addr = yield dut.o_wr_addr
        assert addr == 0x40
        print("passed")

        print("\nall 12 tests passed")

    run_simulation(dut, run(dut), vcd_name="regfile_adapter.vcd")


if __name__ == "__main__":
    tb_regfile_adapter()