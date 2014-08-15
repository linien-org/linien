# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *
from migen.genlib.record import *

# https://github.com/RedPitaya/RedPitaya/blob/master/FPGA/release1/fpga/code/rtl/red_pitaya_daisy.v


sys_layout = [
    ("rstn", 1),
    ("clk", 1),
    ("addr", 32),
    ("wdata", 32),
    ("sel", 4),
    ("wen", 1),
    ("ren", 1),
    ("rdata", 32),
    ("err", 1),
    ("ack", 1),
]


class SysInterconnect(Module):
    def __init__(self, master, *slaves):
        for s in slaves:
            self.comb += [
                    s.clk.eq(master.clk),
                    s.rstn.eq(master.rstn),
                    s.addr.eq(master.addr),
                    s.wdata.eq(master.wdata),
                    s.sel.eq(master.sel),
            ]
        cs = Signal(max=len(slaves))
        self.comb += [
                cs.eq(master.addr[20:23]),
                Array([Cat(s.wen, s.ren) for s in slaves])[cs].eq(
                    Cat(master.wen, master.ren)),
                Cat(master.rdata, master.err, master.ack).eq(
                    Array([Cat(s.rdata, s.err, s.ack) for s in slaves])[cs]),
        ]

cpu_layout = [
       ("FIXED_IO_mio", 54),
       ("FIXED_IO_ps_clk", 1),
       ("FIXED_IO_ps_porb", 1),
       ("FIXED_IO_ps_srstb", 1),
       ("FIXED_IO_ddr_vrn", 1),
       ("FIXED_IO_ddr_vrp", 1),
       ("DDR_addr", 15),
       ("DDR_ba",  3),
       ("DDR_cas_n", 1),
       ("DDR_ck_n", 1),
       ("DDR_ck_p", 1),
       ("DDR_cke", 1),
       ("DDR_cs_n", 1),
       ("DDR_dm",  4),
       ("DDR_dq", 32),
       ("DDR_dqs_n",  4),
       ("DDR_dqs_p",  4),
       ("DDR_odt", 1),
       ("DDR_ras_n", 1),
       ("DDR_reset_n", 1),
       ("DDR_we_n", 1),
]


#     tcl.append("read_xdc ../verilog/dont_touch.xdc")
#     tcl.append("read_xdc -ref processing_system7_v5_4_processing_system7 ../verilog/ system_processing_system7_0_0.xdc")

class RedPid(Module):
    def __init__(self, platform):

        ps_io = platform.request("cpu")
        ps_sys = Record(sys_layout)
        fclk = Signal(4)
        frstn = Signal(4)
        ser_clk = Signal()
        self.specials.ps = Instance("red_pitaya_ps",
            io_FIXED_IO_mio=ps_io.FIXED_IO_mio,
            io_FIXED_IO_ps_clk=ps_io.FIXED_IO_ps_clk,
            io_FIXED_IO_ps_porb=ps_io.FIXED_IO_ps_porb,
            io_FIXED_IO_ps_srstb=ps_io.FIXED_IO_ps_srstb,
            io_FIXED_IO_ddr_vrn=ps_io.FIXED_IO_ddr_vrn,
            io_FIXED_IO_ddr_vrp=ps_io.FIXED_IO_ddr_vrp,
            io_DDR_addr=ps_io.DDR_addr,
            io_DDR_ba=ps_io.DDR_ba,
            io_DDR_cas_n=ps_io.DDR_cas_n,
            io_DDR_ck_n=ps_io.DDR_ck_n,
            io_DDR_ck_p=ps_io.DDR_ck_p,
            io_DDR_cke=ps_io.DDR_cke,
            io_DDR_cs_n=ps_io.DDR_cs_n,
            io_DDR_dm=ps_io.DDR_dm,
            io_DDR_dq=ps_io.DDR_dq,
            io_DDR_dqs_n=ps_io.DDR_dqs_n,
            io_DDR_dqs_p=ps_io.DDR_dqs_p,
            io_DDR_odt=ps_io.DDR_odt,
            io_DDR_ras_n=ps_io.DDR_ras_n,
            io_DDR_reset_n=ps_io.DDR_reset_n,
            io_DDR_we_n=ps_io.DDR_we_n,

            o_fclk_clk_o=fclk,
            o_fclk_rstn_o=frstn,

            o_sys_clk_o=ps_sys.clk,
            o_sys_rstn_o=ps_sys.rstn,
            o_sys_addr_o=ps_sys.addr,
            o_sys_wdata_o=ps_sys.wdata,
            o_sys_sel_o=ps_sys.sel,
            o_sys_wen_o=ps_sys.wen,
            o_sys_ren_o=ps_sys.ren,
            i_sys_rdata_i=ps_sys.rdata,
            i_sys_err_i=ps_sys.err,
            i_sys_ack_i=ps_sys.ack,

            #o_spi_ss_o=spim.ss,
            #o_spi_ss1_o=spim.ss1,
            #o_spi_ss2_o=spim.ss2,
            #o_spi_sclk_o=spim.sclk,
            #o_spi_mosi_o=spim.mosi,
            #i_spi_miso_i=spim.miso,
            i_spi_miso_i=0,

            #i_spi_ss_i=spis.ss,
            #i_spi_sclk_i=spis.sclk,
            #i_spi_mosi_i=spis.mosi,
            #o_spi_miso_o=spis.miso,
            i_spi_ss_i=0,
            i_spi_sclk_i=0,
            i_spi_mosi_i=0,
        )

        self.clock_domains.cd_sys = ClockDomain()
        self.sync += self.cd_sys.rst.eq(frstn[0])

        adc_clk = platform.request("adc_clk")
        adc_clk.cdcs.reset = 1
        adc_clk.clk.reset = 0b10

        clk125 = platform.request("clk125")

        dac = platform.request("dac")

        dac_pwm = Cat(*(platform.request("dac_pwm", i) for i in range(4)))

        io = Record([
            ("ia", (14, True)), ("ib", (14, True)),
            ("oa", (14, True)), ("ob", (14, True))
        ])
        pwm = [Signal(24) for i in range(4)]

        self.specials.analog = Instance("red_pitaya_analog",
                i_adc_dat_a_i=platform.request("adc", 0),
                i_adc_dat_b_i=platform.request("adc", 1),
                i_adc_clk_p_i=clk125.p,
                i_adc_clk_n_i=clk125.n,
                o_dac_dat_o=dac.data,
                o_dac_wrt_o=dac.wrt,
                o_dac_sel_o=dac.sel,
                o_dac_clk_o=platform.request("dac_clk"),
                o_dac_rst_o=dac.rst,
                o_dac_pwm_o=dac_pwm,

                o_adc_dat_a_o=io.ia,
                o_adc_dat_b_o=io.ib,
                o_adc_clk_o=self.cd_sys.clk,
                i_adc_rst_i=ResetSignal(),
                o_ser_clk_o=ser_clk,
                i_dac_dat_a_i=io.oa,
                i_dac_dat_b_i=io.ob,
                i_dac_pwm_a_i=pwm[0],
                i_dac_pwm_b_i=pwm[1],
                i_dac_pwm_c_i=pwm[2],
                i_dac_pwm_d_i=pwm[3],
                #o_dac_pwm_sync_o=,
        )

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
                i_adc_a_i=io.ia,
                i_adc_b_i=io.ib,
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

        self.comb += io.oa.eq(asg[0]), io.ob.eq(asg[1])

        xadc = platform.request("xadc") 
        ams_sys = Record(sys_layout)
        self.specials.ams = Instance("red_pitaya_ams",
                i_clk_i=ClockSignal(),
                i_rstn_i=~ResetSignal(),

                i_vinp_i=xadc.p,
                i_vinn_i=xadc.n,

                o_dac_a_o=pwm[0],
                o_dac_b_o=pwm[1],
                o_dac_c_o=pwm[2],
                o_dac_d_o=pwm[3],

                i_sys_clk_i=ams_sys.clk,
                i_sys_rstn_i=ams_sys.rstn,
                i_sys_addr_i=ams_sys.addr,
                i_sys_wdata_i=ams_sys.wdata,
                i_sys_sel_i=ams_sys.sel,
                i_sys_wen_i=ams_sys.wen,
                i_sys_ren_i=ams_sys.ren,
                o_sys_rdata_o=ams_sys.rdata,
                o_sys_err_o=ams_sys.err,
                o_sys_ack_o=ams_sys.ack,
        )

        sata0 = platform.request("sata", 0)
        sata1 = platform.request("sata", 1)
        daisy_rdy = Signal()
        daisy_sys = Record(sys_layout)
        self.specials.ams = Instance("red_pitaya_daisy",
                o_daisy_p_o=Cat(sata0.rx_p, sata0.tx_p),
                o_daisy_n_o=Cat(sata0.rx_n, sata0.tx_n),
                i_daisy_p_i=Cat(sata1.rx_p, sata1.tx_p),
                i_daisy_n_i=Cat(sata1.rx_n, sata1.tx_n),

                i_ser_clk_i=ser_clk,
                i_dly_clk_i=fclk[3],

                i_par_clk_i=ClockSignal(),
                i_par_rstn_i=~ResetSignal(),
                o_par_rdy_o=daisy_rdy,
                i_par_dv_i=daisy_rdy,
                i_par_dat_i=0x1234,
                #o_par_clk_o=,
                #o_par_rstn_o=,
                #o_par_dv_o=,
                #o_par_dat_o=,
                #o_debug_o=,

                i_sys_clk_i=daisy_sys.clk,
                i_sys_rstn_i=daisy_sys.rstn,
                i_sys_addr_i=daisy_sys.addr,
                i_sys_wdata_i=daisy_sys.wdata,
                i_sys_sel_i=daisy_sys.sel,
                i_sys_wen_i=daisy_sys.wen,
                i_sys_ren_i=daisy_sys.ren,
                o_sys_rdata_o=daisy_sys.rdata,
                o_sys_err_o=daisy_sys.err,
                o_sys_ack_o=daisy_sys.ack,
        )

        pid_sys = Record(sys_layout)
        pid_sys.ack.reset = 1
        unused_sys = Record(sys_layout)
        unused_sys.ack.reset = 1
        test_sys = Record(sys_layout)
        test_sys.ack.reset = 1

        self.submodules.intercon = SysInterconnect(ps_sys,
                hk_sys, scope_sys, asg_sys, pid_sys,
                ams_sys, daisy_sys, unused_sys, test_sys)
