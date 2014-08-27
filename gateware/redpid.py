# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bus import csr
from migen.bank import csrgen

# https://github.com/RedPitaya/RedPitaya/blob/master/FPGA/release1/fpga/code/rtl/red_pitaya_daisy.v

from .pitaya_ps import SysCDC, Sys2CSR, SysInterconnect, PitayaPS, sys_layout
from .crg import CRG
from .analog import PitayaAnalog
from .pid import Pid
from .slow import Slow

#     tcl.append("read_xdc -ref processing_system7_v5_4_processing_system7 ../verilog/ system_processing_system7_0_0.xdc")

class RedPid(Module):
    def __init__(self, platform):

        self.submodules.ps = PitayaPS(platform.request("cpu"))

        self.submodules.crg = CRG(platform.request("clk125"), ~self.ps.frstn[0])

        self.submodules.analog = PitayaAnalog(platform.request("adc"),
            platform.request("dac"))

        xadc = platform.request("xadc")
        pwm = Cat(platform.request("pwm", i) for i in range(4))
        exp = platform.request("exp")
        leds = Cat(*(platform.request("user_led", i) for i in range(8)))

        self.submodules.slow = Slow(exp, pwm, leds, xadc)

        asg_trig = Signal()

        scope_sys = Record(sys_layout)
        self.specials.scope = Instance("red_pitaya_scope",
                i_adc_a_i=self.analog.adc_a,
                i_adc_b_i=self.analog.adc_b,
                i_adc_clk_i=ClockSignal(),
                i_adc_rstn_i=1,
                i_trig_ext_i=self.slow.gpio_p._r_in.status[0],
                i_trig_asg_i=asg_trig,

                i_sys_clk_i=scope_sys.clk,
                i_sys_rstn_i=scope_sys.rstn,
                i_sys_addr_i=scope_sys.addr,
                i_sys_wdata_i=scope_sys.wdata,
                i_sys_sel_i=scope_sys.sel,
                i_sys_wen_i=scope_sys.wen,
                i_sys_ren_i=scope_sys.ren,
                o_sys_rdata_o=scope_sys.rdata,
                o_sys_err_o=scope_sys.err,
                o_sys_ack_o=scope_sys.ack,
        )

        asg = [Signal((14, True)) for i in range(2)]

        asg_sys = Record(sys_layout)
        self.specials.asg = Instance("red_pitaya_asg",
                o_dac_a_o=asg[0],
                o_dac_b_o=asg[1],
                i_dac_clk_i=ClockSignal(),
                i_dac_rstn_i=1,
                i_trig_a_i=self.slow.gpio_p._r_in.status[0],
                i_trig_b_i=self.slow.gpio_p._r_in.status[0],
                o_trig_out_o=asg_trig,

                i_sys_clk_i=asg_sys.clk,
                i_sys_rstn_i=asg_sys.rstn,
                i_sys_addr_i=asg_sys.addr,
                i_sys_wdata_i=asg_sys.wdata,
                i_sys_sel_i=asg_sys.sel,
                i_sys_wen_i=asg_sys.wen,
                i_sys_ren_i=asg_sys.ren,
                o_sys_rdata_o=asg_sys.rdata,
                o_sys_err_o=asg_sys.err,
                o_sys_ack_o=asg_sys.ack,
        )

        self.submodules.pid = Pid()

        self.comb += [
                self.pid.out_a.asg.eq(asg[0]),
                self.pid.out_b.asg.eq(asg[1]),
                self.pid.in_a.adc.eq(self.analog.adc_a),
                self.pid.in_b.adc.eq(self.analog.adc_b),
                self.analog.dac_a.eq(self.pid.out_a.dac),
                self.analog.dac_b.eq(self.pid.out_b.dac)
        ]

        csr_map = {"pid": 0, "slow": 1}
        self.submodules.csrbanks = csrgen.BankArray(self,
                    lambda name, mem: csr_map[name if mem is None
                        else name + "_" + mem.name_override])
        self.submodules.sys2csr = Sys2CSR()
        self.submodules.csrcon = csr.Interconnect(self.sys2csr.csr,
                self.csrbanks.get_buses())
        self.submodules.syscdc = SysCDC()
        self.comb += self.syscdc.target.connect(self.sys2csr.sys)

        hk_sys = Record(sys_layout)
        self.submodules.ic = SysInterconnect(self.ps.axi.sys,
                hk_sys, scope_sys, asg_sys, self.syscdc.source)
