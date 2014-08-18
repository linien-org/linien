from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bus import wishbone



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


axi_layout = [
        ("arvalid", 1),
        ("awvalid", 1),
        ("bready", 1),
        ("rready", 1),
        ("wlast", 1),
        ("wvalid", 1),
        ("arid", 12),
        ("awid", 12),
        ("wid", 12),
        ("arburst", 2),
        ("arlock", 2),
        ("arsize", 3),
        ("awburst", 2),
        ("awlock", 2),
        ("awsize", 3),
        ("arprot", 3),
        ("awprot", 3),
        ("araddr", 32),
        ("awaddr", 32),
        ("wdata", 32),
        ("arcache", 4),
        ("arlen", 4),
        ("arqos", 4),
        ("awcache", 4),
        ("awlen", 4),
        ("awqos", 4),
        ("wstrb", 4),
        ("aclk", 1),
        ("arready", 1),
        ("awready", 1),
        ("bvalid", 1),
        ("rlast", 1),
        ("rvalid", 1),
        ("wready", 1),
        ("bid", 12),
        ("rid", 12),
        ("bresp", 2),
        ("rresp", 2),
        ("rdata", 32),
        ("arstn", 1),
]


class PitayaPS(Module):
    def __init__(self, cpu):
        self.fclk = Signal(4)
        self.frstn = Signal(4)
        
        ###

        self.submodules.axi = Axi2Sys()
        axi = self.axi.axi
        self.comb += [
                axi.aclk.eq(self.fclk[0]),
                axi.arstn.eq(self.frstn[0]),
        ]

        self.specials += Instance("system_wrapper",
                io_FIXED_IO_mio=cpu.FIXED_IO_mio,
                io_FIXED_IO_ps_clk=cpu.FIXED_IO_ps_clk,
                io_FIXED_IO_ps_porb=cpu.FIXED_IO_ps_porb,
                io_FIXED_IO_ps_srstb=cpu.FIXED_IO_ps_srstb,
                io_FIXED_IO_ddr_vrn=cpu.FIXED_IO_ddr_vrn,
                io_FIXED_IO_ddr_vrp=cpu.FIXED_IO_ddr_vrp,
                io_DDR_addr=cpu.DDR_addr,
                io_DDR_ba=cpu.DDR_ba,
                io_DDR_cas_n=cpu.DDR_cas_n,
                io_DDR_ck_n=cpu.DDR_ck_n,
                io_DDR_ck_p=cpu.DDR_ck_p,
                io_DDR_cke=cpu.DDR_cke,
                io_DDR_cs_n=cpu.DDR_cs_n,
                io_DDR_dm=cpu.DDR_dm,
                io_DDR_dq=cpu.DDR_dq,
                io_DDR_dqs_n=cpu.DDR_dqs_n,
                io_DDR_dqs_p=cpu.DDR_dqs_p,
                io_DDR_odt=cpu.DDR_odt,
                io_DDR_ras_n=cpu.DDR_ras_n,
                io_DDR_reset_n=cpu.DDR_reset_n,
                io_DDR_we_n=cpu.DDR_we_n,

                o_FCLK_CLK0=self.fclk[0],
                o_FCLK_CLK1=self.fclk[1],
                o_FCLK_CLK2=self.fclk[2],
                o_FCLK_CLK3=self.fclk[3],
                o_FCLK_RESET0_N=self.frstn[0],
                o_FCLK_RESET1_N=self.frstn[1],
                o_FCLK_RESET2_N=self.frstn[2],
                o_FCLK_RESET3_N=self.frstn[3],

                o_M_AXI_GP0_arvalid=axi.arvalid,
                o_M_AXI_GP0_awvalid=axi.awvalid,
                o_M_AXI_GP0_bready=axi.bready,
                o_M_AXI_GP0_rready=axi.rready,
                o_M_AXI_GP0_wlast=axi.wlast,
                o_M_AXI_GP0_wvalid=axi.wvalid,
                o_M_AXI_GP0_arid=axi.arid,
                o_M_AXI_GP0_awid=axi.awid,
                o_M_AXI_GP0_wid=axi.wid,
                o_M_AXI_GP0_arburst=axi.arburst,
                o_M_AXI_GP0_arlock=axi.arlock,
                o_M_AXI_GP0_arsize=axi.arsize,
                o_M_AXI_GP0_awburst=axi.awburst,
                o_M_AXI_GP0_awlock=axi.awlock,
                o_M_AXI_GP0_awsize=axi.awsize,
                o_M_AXI_GP0_arprot=axi.arprot,
                o_M_AXI_GP0_awprot=axi.awprot,
                o_M_AXI_GP0_araddr=axi.araddr,
                o_M_AXI_GP0_awaddr=axi.awaddr,
                o_M_AXI_GP0_wdata=axi.wdata,
                o_M_AXI_GP0_arcache=axi.arcache,
                o_M_AXI_GP0_arlen=axi.arlen,
                o_M_AXI_GP0_arqos=axi.arqos,
                o_M_AXI_GP0_awcache=axi.awcache,
                o_M_AXI_GP0_awlen=axi.awlen,
                o_M_AXI_GP0_awqos=axi.awqos,
                o_M_AXI_GP0_wstrb=axi.wstrb,
                i_M_AXI_GP0_arready=axi.arready,
                i_M_AXI_GP0_awready=axi.awready,
                i_M_AXI_GP0_bvalid=axi.bvalid,
                i_M_AXI_GP0_rlast=axi.rlast,
                i_M_AXI_GP0_rvalid=axi.rvalid,
                i_M_AXI_GP0_wready=axi.wready,
                i_M_AXI_GP0_bid=axi.bid,
                i_M_AXI_GP0_rid=axi.rid,
                i_M_AXI_GP0_bresp=axi.bresp,
                i_M_AXI_GP0_rresp=axi.rresp,
                i_M_AXI_GP0_rdata=axi.rdata,
                #i_SPI0_SS_I=spi.ss_i,
                i_SPI0_SS_I=0,
                #o_SPI0_SS_O=spi.ss_o,
                #o_SPI0_SS1_O=spi.ss1_o,
                #o_SPI0_SS2_O=spi.ss2_o,
                #i_SPI0_SCLK_I=spi.sclk_i,
                i_SPI0_SCLK_I=0,
                #o_SPI0_SCLK_O=spi.sclk_o,
                #i_SPI0_MOSI_I=spi.mosi_i,
                i_SPI0_MOSI_I=0,
                #o_SPI0_MOSI_O=spi.mosi_o,
                #i_SPI0_MISO_I=spi.miso_i,
                i_SPI0_MISO_I=0,
                #o_SPI0_MISO_O=spi.miso_o,
                #o_SPIO_SS_T=,
                #o_SPIO_SCLK_T=,
                #o_SPIO_MOSI_T=,
                #o_SPIO_MISO_T=,
        )



class Axi2Sys(Module):
    def __init__(self):
        self.sys = Record(sys_layout)
        self.axi = Record(axi_layout)

        ###

        self.comb += [
                self.sys.clk.eq(self.axi.aclk),
                self.sys.rstn.eq(self.axi.arstn)
        ]

        self.specials += Instance("axi_slave",
                p_AXI_DW=32,
                p_AXI_AW=32,
                p_AXI_IW=12,

                i_axi_clk_i=self.axi.aclk,
                i_axi_rstn_i=self.axi.arstn,

                i_axi_awid_i=self.axi.awid,
                i_axi_awaddr_i=self.axi.awaddr,
                i_axi_awlen_i=self.axi.awlen,
                i_axi_awsize_i=self.axi.awsize,
                i_axi_awburst_i=self.axi.awburst,
                i_axi_awlock_i=self.axi.awlock,
                i_axi_awcache_i=self.axi.awcache,
                i_axi_awprot_i=self.axi.awprot,
                i_axi_awvalid_i=self.axi.awvalid,
                o_axi_awready_o=self.axi.awready,

                i_axi_wid_i=self.axi.wid,
                i_axi_wdata_i=self.axi.wdata,
                i_axi_wstrb_i=self.axi.wstrb,
                i_axi_wlast_i=self.axi.wlast,
                i_axi_wvalid_i=self.axi.wvalid,
                o_axi_wready_o=self.axi.wready,

                o_axi_bid_o=self.axi.bid,
                o_axi_bresp_o=self.axi.bresp,
                o_axi_bvalid_o=self.axi.bvalid,
                i_axi_bready_i=self.axi.bready,

                i_axi_arid_i=self.axi.arid,
                i_axi_araddr_i=self.axi.araddr,
                i_axi_arlen_i=self.axi.arlen,
                i_axi_arsize_i=self.axi.arsize,
                i_axi_arburst_i=self.axi.arburst,
                i_axi_arlock_i=self.axi.arlock,
                i_axi_arcache_i=self.axi.arcache,
                i_axi_arprot_i=self.axi.arprot,
                i_axi_arvalid_i=self.axi.arvalid,
                o_axi_arready_o=self.axi.arready,
    
                o_axi_rid_o=self.axi.rid,
                o_axi_rdata_o=self.axi.rdata,
                o_axi_rresp_o=self.axi.rresp,
                o_axi_rlast_o=self.axi.rlast,
                o_axi_rvalid_o=self.axi.rvalid,
                i_axi_rready_i=self.axi.rready,

                o_sys_addr_o=self.sys.addr,
                o_sys_wdata_o=self.sys.wdata,
                o_sys_sel_o=self.sys.sel,
                o_sys_wen_o=self.sys.wen,
                o_sys_ren_o=self.sys.ren,
                i_sys_rdata_i=self.sys.rdata,
                i_sys_err_i=self.sys.err,
                i_sys_ack_i=self.sys.ack,
        )


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


class Sys2Wishbone(Module):
    def __init__(self):
        self.wishbone = wb = wishbone.Interface()
        self.sys = Record(sys_layout)

        ###

        adr = Signal.like(self.sys.addr)
        re = Signal()

        self.specials += Instance("bus_clk_bridge",
                i_sys_clk_i=self.sys.clk, i_sys_rstn_i=self.sys.rstn,
                i_sys_addr_i=self.sys.addr, i_sys_wdata_i=self.sys.wdata,
                i_sys_sel_i=self.sys.sel, i_sys_wen_i=self.sys.wen,
                i_sys_ren_i=self.sys.ren, o_sys_rdata_o=self.sys.rdata,
                o_sys_err_o=self.sys.err, o_sys_ack_o=self.sys.ack,

                i_clk_i=ClockSignal(), i_rstn_i=ResetSignal(),
                o_addr_o=adr, o_wdata_o=wb.dat_w, o_wen_o=wb.we,
                o_ren_o=re, i_rdata_i=wb.dat_r, i_err_i=wb.err,
                i_ack_i=wb.ack,
        )
        self.comb += [
                wb.stb.eq(re | wb.we),
                wb.cyc.eq(wb.stb),
                wb.adr.eq(adr[2:]),
        ]
