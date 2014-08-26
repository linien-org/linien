# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bus import csr
from migen.bank import csrgen

# https://github.com/RedPitaya/RedPitaya/blob/master/FPGA/release1/fpga/code/rtl/red_pitaya_daisy.v

from .pitaya_ps import SysCDC, Sys2CSR, SysInterconnect, PitayaPS, sys_layout
from .crg import CRG
from .xadc import XADC
from .delta_sigma import DeltaSigmaCSR
from .analog import PitayaAnalog
from .pid import Pid


#     tcl.append("read_xdc -ref processing_system7_v5_4_processing_system7 ../verilog/ system_processing_system7_0_0.xdc")

class RedPid(Module):
    def __init__(self, platform):

        self.submodules.ps = PitayaPS(platform.request("cpu"))

        self.submodules.crg = CRG(platform.request("clk125"), ~self.ps.frstn[0])

        self.submodules.analog = PitayaAnalog(platform.request("adc"),
            platform.request("dac"))

        pwm = Cat(platform.request("pwm", i) for i in range(4))
        pwm_o = Signal(flen(pwm))
        self.comb += pwm.eq(pwm_o)
        self.submodules.deltasigma = DeltaSigmaCSR(pwm_o, width=24)

        self.submodules.xadc = XADC(platform.request("xadc"))

        exp_q = platform.request("exp")
        n = flen(exp_q.p)
        exp = Record([
            ("pi", n), ("ni", n),
            ("po", n), ("no", n),
            ("pt", n), ("nt", n),
        ])
        for i in range(n):
            self.specials += Instance("IOBUF",
                    o_O=exp.pi[i], io_IO=exp_q.p[i], i_I=exp.po[i], i_T=exp.pt[i])
            self.specials += Instance("IOBUF",
                    o_O=exp.ni[i], io_IO=exp_q.n[i], i_I=exp.no[i], i_T=exp.nt[i])
        leds = Cat(*(platform.request("user_led", i) for i in range(n)))

        hk_sys = Record(sys_layout)
        self.specials.hk = Instance("red_pitaya_hk",
                i_clk_i=ClockSignal(),
                i_rstn_i=~ResetSignal(),
                o_led_o=leds,
                i_exp_p_dat_i=exp.pi,
                i_exp_n_dat_i=exp.ni,
                o_exp_p_dir_o=exp.pt,
                o_exp_n_dir_o=exp.nt,
                o_exp_p_dat_o=exp.po,
                o_exp_n_dat_o=exp.no,

                i_sys_clk_i=hk_sys.clk,
                i_sys_rstn_i=hk_sys.rstn,
                i_sys_addr_i=hk_sys.addr,
                i_sys_wdata_i=hk_sys.wdata,
                i_sys_sel_i=hk_sys.sel,
                i_sys_wen_i=hk_sys.wen,
                i_sys_ren_i=hk_sys.ren,
                o_sys_rdata_o=hk_sys.rdata,
                o_sys_err_o=hk_sys.err,
                o_sys_ack_o=hk_sys.ack,
        )

        asg_trig = Signal()

        scope_sys = Record(sys_layout)
        self.specials.scope = Instance("red_pitaya_scope",
                i_adc_a_i=self.analog.adc_a,
                i_adc_b_i=self.analog.adc_b,
                i_adc_clk_i=ClockSignal(),
                i_adc_rstn_i=~ResetSignal(),
                i_trig_ext_i=exp.pi[0],
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
                i_dac_rstn_i=~ResetSignal(),
                i_trig_a_i=exp.pi[0],
                i_trig_b_i=exp.pi[0],
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

        csr_map = {"pid": 0, "deltasigma": 1, "xadc": 2}
        self.submodules.csrbanks = csrgen.BankArray(self,
                    lambda name, mem: csr_map[name if mem is None
                        else name + "_" + mem.name_override])
        self.submodules.sys2csr = Sys2CSR()
        self.submodules.csrcon = csr.Interconnect(self.sys2csr.csr,
                self.csrbanks.get_buses())
        self.submodules.syscdc = SysCDC()
        self.comb += self.syscdc.target.connect(self.sys2csr.sys)

        self.submodules.ic = SysInterconnect(self.ps.axi.sys,
                hk_sys, scope_sys, asg_sys, self.syscdc.source)
