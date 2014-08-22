# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bus import csr
from migen.bank import csrgen

# https://github.com/RedPitaya/RedPitaya/blob/master/FPGA/release1/fpga/code/rtl/red_pitaya_daisy.v

from .delta_sigma import DeltaSigmaCSR
from .pid import Pid
from .pitaya_ps import SysCDC, Sys2CSR, SysInterconnect, PitayaPS, sys_layout



class CRG(Module):
    def __init__(self, clk_adc, rst):
        self.clock_domains.cd_adc = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys2 = ClockDomain(reset_less=True)

        clk_adci, clk_adcb = Signal(), Signal()
        clk, clkb = Signal(6), Signal(6)
        clk_fb, clk_fbb = Signal(), Signal()
        locked = Signal()
        self.specials += [
                Instance("IBUFGDS", i_I=clk_adc.p, i_IB=clk_adc.n, o_O=clk_adci),
                Instance("BUFG", i_I=clk_adci, o_O=clk_adcb),
                #Instance("BUFR", i_I=clk_adci, o_O=self.cd_adc.clk), # too fast
        ]
        self.comb += self.cd_adc.clk.eq(clk_adcb)
        self.specials += [
                Instance("PLLE2_BASE",
                    p_BANDWIDTH="OPTIMIZED",
                    p_DIVCLK_DIVIDE=1,
                    p_CLKFBOUT_PHASE=0.,
                    p_CLKFBOUT_MULT=8,
                    p_CLKIN1_PERIOD=8.,
                    p_REF_JITTER1=0.01,
                    p_STARTUP_WAIT="FALSE",
                    i_CLKIN1=clk_adcb, i_PWRDWN=0, i_RST=rst,
                    i_CLKFBIN=clk_fbb, o_CLKFBOUT=clk_fb,
                    p_CLKOUT0_DIVIDE=8, p_CLKOUT0_PHASE=0.,
                    p_CLKOUT0_DUTY_CYCLE=0.5, o_CLKOUT0=clk[0],
                    p_CLKOUT1_DIVIDE=4, p_CLKOUT1_PHASE=0.,
                    p_CLKOUT1_DUTY_CYCLE=0.5, o_CLKOUT1=clk[1],
                    p_CLKOUT2_DIVIDE=2, p_CLKOUT2_PHASE=0.,
                    p_CLKOUT2_DUTY_CYCLE=0.5, o_CLKOUT2=clk[2],
                    p_CLKOUT3_DIVIDE=4, p_CLKOUT3_PHASE=0.,
                    p_CLKOUT3_DUTY_CYCLE=0.5, o_CLKOUT3=clk[3],
                    p_CLKOUT4_DIVIDE=4, p_CLKOUT4_PHASE=0.,
                    p_CLKOUT4_DUTY_CYCLE=0.5, o_CLKOUT4=clk[4],
                    p_CLKOUT5_DIVIDE=4, p_CLKOUT5_PHASE=0.,
                    p_CLKOUT5_DUTY_CYCLE=0.5, o_CLKOUT5=clk[5],
                    o_LOCKED=locked,
                )
        ]
        self.specials += Instance("BUFG", i_I=clk_fb, o_O=clk_fbb)
        for i, o, d in zip(clk, clkb, [self.cd_sys, self.cd_sys2]):
            self.specials += Instance("BUFG", i_I=i, o_O=d.clk)
        self.specials += Instance("FD", p_INIT=1, i_D=~locked, i_C=self.cd_sys.clk,
                o_Q=self.cd_sys.rst)




class PitayaAnalog(Module):
    def __init__(self, adc, dac):
        self.comb += adc.cdcs.eq(1), adc.clk.eq(0b10)

        sign = 1<<(flen(dac.data) - 1)
        size = flen(dac.data), True

        self.adc_a, self.adc_b = Signal(size), Signal(size)
        self.dac_a, self.dac_b = Signal(size), Signal(size)

        adca, adcb = Signal.like(adc.data_a), Signal.like(adc.data_b)
        self.sync.adc += adca.eq(adc.data_a), adcb.eq(adc.data_b)
        #self.sync += self.adc_a.eq(-(sign ^ adca[2:])), self.adc_b.eq(-(sign ^ adcb[2:]))
        self.sync += [ # this is off by one LSB but otherwise min and max fail
                self.adc_a.eq(Cat(~adca[2:-1], adca[-1])),
                self.adc_b.eq(Cat(~adcb[2:-1], adcb[-1]))
        ]

        daca, dacb = Signal.like(dac.data), Signal.like(dac.data)
        #dacai, dacbi = Signal.like(dac.data), Signal.like(dac.data)
        #self.comb += dacai.eq(-self.dac_a), dacbi.eq(-self.dac_b)
        #self.sync += daca.eq(dacai ^ sign), dacb.eq(dacbi ^ sign)
        self.comb += [
                daca.eq(Cat(~self.dac_a[2:-1], self.dac_a[-1])),
                dacb.eq(Cat(~self.dac_b[2:-1], self.dac_b[-1]))
        ]

        self.comb += dac.rst.eq(ResetSignal("sys"))
        self.specials += [
                Instance("ODDR", i_D1=0, i_D2=1, i_C=ClockSignal("sys2"),
                    o_Q=dac.clk, i_CE=1, i_R=0, i_S=0),
                Instance("ODDR", i_D1=0, i_D2=1, i_C=ClockSignal("sys2"),
                    o_Q=dac.wrt, i_CE=1, i_R=0, i_S=0),
                Instance("ODDR", i_D1=0, i_D2=1, i_C=ClockSignal("sys"),
                    o_Q=dac.sel, i_CE=1, i_R=0, i_S=0),
                [Instance("ODDR", i_D1=a, i_D2=b, i_C=ClockSignal("sys"),
                    o_Q=d, i_CE=1, i_R=0, i_S=0)
                    for a, b, d in zip(daca, dacb, dac.data)]
        ]


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

        csr_map = {"pid": 0, "deltasigma": 1}
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
