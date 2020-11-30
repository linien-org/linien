from migen import Signal, Module, Instance, ClockSignal, ResetSignal, Array, Record
from misoc.interconnect.csr import AutoCSR, CSRStorage
from .pitaya_ps import sys_layout


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
        )
