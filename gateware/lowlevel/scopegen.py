from migen import Signal, Module, Instance, ClockSignal, ResetSignal, Array, Record, ClockDomain, ClockDomainsRenamer, If
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from .pitaya_ps import sys_layout


class Tester(Module):
    def __init__(self):
        self.counter = Signal(14)
        self.value = Signal((14, True))
        self.to_compare = Signal((14, True))

        #self.sign = Signal((2, True), reset=1)
        self.at_start = Signal()

        self.sync += [
            If((self.value > self.to_compare) & ~self.at_start,
                self.counter.eq(
                    self.counter + 1
                )
            ),
            If(self.at_start,
                self.counter.eq(0)
            )
        ]


class ScopeGen(Module, AutoCSR):
    def __init__(self, width=25):
        self.gpio_trigger = Signal()
        self.sweep_trigger = Signal()

        self.external_trigger = CSRStorage(1)
        ext_scope_trigger = Array([
            self.gpio_trigger,
            self.sweep_trigger
        ])[self.external_trigger.storage]

        self.scope_sys = Record(sys_layout)
        self.asg_sys = Record(sys_layout)

        adc_a = Signal((width, True))
        adc_a_q = Signal((width, True))
        adc_b = Signal((width, True))
        adc_b_q = Signal((width, True))
        dac_a = Signal((width, True))
        dac_b = Signal((width, True))

        self.signal_in = adc_a, adc_b, adc_a_q, adc_b_q
        self.signal_out = dac_a, dac_b
        self.state_in = ()
        self.state_out = ()

        asg_a = Signal((14, True))
        asg_b = Signal((14, True))
        asg_trig = Signal()

        s = width - len(asg_a)
        self.comb += dac_a.eq(asg_a << s), dac_b.eq(asg_b << s)


        scope_written_data = Signal((14, True))
        scope_position = Signal(14)

        self.to_compare = CSRStorage(14)
        self.N_greater = CSRStatus(14)
        #self.sign = CSRStorage(2)

        self.clock_domains.cd_tester_clock = ClockDomain('tester_clock')
        renamed_clock = ClockDomainsRenamer("tester_clock")

        self.submodules.tester = renamed_clock(Tester())

        self.comb += [
            self.tester.value.eq(scope_written_data),
            self.tester.to_compare.eq(self.to_compare.storage),
            self.N_greater.status.eq(self.tester.counter),
            self.tester.at_start.eq(
                scope_position == 0
            ),
            #self.tester.sign.eq(self.sign)
        ]
        scope_writing_now = Signal()

        self.comb += [
            self.cd_tester_clock.clk.eq(scope_writing_now)
        ]

        self.specials.scope = Instance("red_pitaya_scope",
                i_adc_a_i=adc_a >> s,
                i_adc_b_i=adc_b >> s,
                i_adc_a_q_i=adc_a_q >> s,
                i_adc_b_q_i=adc_b_q >> s,
                #i_adc_a_q_i=0b11111111111111,
                #i_adc_b_q_i=0b11111111111111,
                i_adc_clk_i=ClockSignal(),
                i_adc_rstn_i=~ResetSignal(),

                i_trig_ext_i=ext_scope_trigger,
                i_trig_asg_i=asg_trig,

                i_sys_clk_i=self.scope_sys.clk,
                i_sys_rstn_i=self.scope_sys.rstn,
                i_sys_addr_i=self.scope_sys.addr,
                i_sys_wdata_i=self.scope_sys.wdata,
                i_sys_sel_i=self.scope_sys.sel,
                i_sys_wen_i=self.scope_sys.wen,
                i_sys_ren_i=self.scope_sys.ren,
                o_sys_rdata_o=self.scope_sys.rdata,
                o_sys_err_o=self.scope_sys.err,
                o_sys_ack_o=self.scope_sys.ack,

                o_written_data=scope_written_data,
                o_scope_position=scope_position,
                o_scope_writing_now=scope_writing_now
        )


def tester_testbench(tester):
    yield tester.to_compare.eq(123)
    yield tester.value.eq(124)
    yield

    yield
    yield
    yield
    yield
    yield

    counter = yield tester.counter
    assert counter == 5

    yield tester.at_start.eq(1)
    yield
    yield
    counter = yield tester.counter
    assert counter == 0

    yield tester.at_start.eq(0)
    yield tester.to_compare.eq(50)
    yield
    for i in range(100):
        yield tester.value.eq(i)
        yield

    counter = yield tester.counter
    assert counter == 49
    """

    yield tester.at_start.eq(1)
    yield tester.sign.eq(-1)

    yield

    yield tester.at_start.eq(0)"""


if __name__ == '__main__':
    from migen import run_simulation

    tester = Tester()
    run_simulation(tester, tester_testbench(tester))