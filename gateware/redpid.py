# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bus import wishbone

# https://github.com/RedPitaya/RedPitaya/blob/master/FPGA/release1/fpga/code/rtl/red_pitaya_daisy.v

from .delta_sigma import DeltaSigma
from .pid import Pid
from .pitaya_ps import Sys2Wishbone, SysInterconnect, PitayaPS, sys_layout



class CRG(Module):
    def __init__(self, clk_adc, rst):
        self.clock_domains.cd_adc = ClockDomain()
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys4 = ClockDomain()
        self.clock_domains.cd_sys2p = ClockDomain()
        self.clock_domains.cd_sys2 = ClockDomain()
        self.clock_domains.cd_ser = ClockDomain()

        clk_adci, clk_adcb = Signal(), Signal()
        clk, clkb = Signal(6), Signal(6)
        clk_fb, clk_fbb = Signal(), Signal()
        locked = Signal()
        self.specials += [
                Instance("IBUFDS", i_I=clk_adc.p, i_IB=clk_adc.n, o_O=clk_adci),
                Instance("BUFG", i_I=clk_adci, o_O=clk_adcb),
        ]
        self.comb += self.cd_adc.clk.eq(clk_adcb)
        self.specials += Instance("FD", p_INIT=1, i_D=~locked, i_C=self.cd_adc.clk,
                o_Q=self.cd_adc.rst)
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
                    p_CLKOUT1_DIVIDE=2, p_CLKOUT1_PHASE=0.,
                    p_CLKOUT1_DUTY_CYCLE=0.5, o_CLKOUT1=clk[1],
                    p_CLKOUT2_DIVIDE=4, p_CLKOUT2_PHASE=-45.,
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
        for i, o, d in zip(clk, clkb,
                [self.cd_sys, self.cd_sys4, self.cd_sys2p, self.cd_sys2,
                    self.cd_ser]):
            self.specials += [
                    Instance("BUFG", i_I=i, o_O=d.clk),
                    Instance("FD", p_INIT=1, i_D=~locked, i_C=d.clk, o_Q=d.rst)
            ]




class PitayaAnalog(Module):
    def __init__(self, adc, dac):
        self.comb += adc.cdcs.eq(1), adc.clk.eq(0b10)

        sign = 1<<(flen(dac.data) - 1)
        size = flen(dac.data), True

        self.adc_a, self.adc_b = Signal(size), Signal(size)
        self.dac_a, self.dac_b = Signal(size), Signal(size)

        adca, adcb = Signal(size), Signal(size)
        self.sync.adc += adca.eq(sign ^ adc.data_a[2:]), adcb.eq(sign ^ adc.data_b[2:])
        self.sync += self.adc_a.eq(-adca), self.adc_b.eq(-adcb)

        daca, dacb = Signal.like(dac.data), Signal.like(dac.data)
        self.sync += daca.eq(sign ^ -self.dac_a), dacb.eq(sign ^ -self.dac_b)

        self.comb += dac.rst.eq(ResetSignal())
        self.specials += [
                Instance("ODDR", i_D1=0, i_D2=1, i_C=ClockSignal("sys2p"),
                    o_Q=dac.clk, i_CE=1, i_R=0, i_S=0),
                Instance("ODDR", i_D1=0, i_D2=1, i_C=ClockSignal("sys2"),
                    o_Q=dac.wrt, i_CE=1, i_R=0, i_S=0),
                Instance("ODDR", i_D1=1, i_D2=0, i_C=ClockSignal(),
                    o_Q=dac.sel, i_CE=1, i_R=0, i_S=0),
                [Instance("ODDR", i_D1=bi, i_D2=ai, i_C=ClockSignal(),
                    o_Q=di, i_CE=1, i_R=0, i_S=0)
                    for ai, bi, di in zip(daca, dacb, dac.data)]
        ]


#     tcl.append("read_xdc ../verilog/dont_touch.xdc")
#     tcl.append("read_xdc -ref processing_system7_v5_4_processing_system7 ../verilog/ system_processing_system7_0_0.xdc")

class RedPid(Module):
    def __init__(self, platform):

        self.submodules.ps = PitayaPS(platform.request("cpu"))

        self.submodules.crg = CRG(platform.request("clk125"), ~self.ps.frstn[0])

        self.submodules.analog = PitayaAnalog(platform.request("adc"),
            platform.request("dac"))

        pwm = []
        for i in range(4):
            ds = DeltaSigma(width=24)
            self.submodules += ds
            self.comb += platform.request("pwm", i).eq(ds.out)
            pwm.append(ds.data)

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
        self.submodules.sys2wb = Sys2Wishbone()
        self.submodules.wbcon = wishbone.InterconnectPointToPoint(
                self.sys2wb.wishbone, self.pid.wishbone)
        self.comb += [
                self.pid.ins[0].eq(self.analog.adc_a),
                self.pid.ins[1].eq(self.analog.adc_b),
                self.analog.dac_a.eq(asg[0] + self.pid.outs[0]),
                self.analog.dac_b.eq(asg[1] + self.pid.outs[1])
        ]

        self.submodules.intercon = SysInterconnect(self.ps.axi.sys,
                hk_sys, scope_sys, asg_sys, self.sys2wb.sys)
