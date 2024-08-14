# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

from functools import reduce
from operator import or_

from migen import (
    DIR_M_TO_S,
    DIR_S_TO_M,
    Cat,
    ClockSignal,
    If,
    Instance,
    Module,
    Record,
    Replicate,
    ResetSignal,
    Signal,
)
from misoc.interconnect import csr_bus, wishbone

sys_layout = [
    ("rstn", 1, DIR_M_TO_S),
    ("clk", 1, DIR_M_TO_S),
    ("addr", 32, DIR_M_TO_S),
    ("wdata", 32, DIR_M_TO_S),
    ("sel", 4, DIR_M_TO_S),
    ("wen", 1, DIR_M_TO_S),
    ("ren", 1, DIR_M_TO_S),
    ("rdata", 32, DIR_S_TO_M),
    ("err", 1, DIR_S_TO_M),
    ("ack", 1, DIR_S_TO_M),
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

        self.specials += Instance(
            "system_processing_system7_0_0",
            io_MIO=cpu.mio,
            io_PS_CLK=cpu.ps_clk,
            io_PS_PORB=cpu.ps_porb,
            io_PS_SRSTB=cpu.ps_srstb,
            io_DDR_Addr=cpu.DDR_addr,
            io_DDR_BankAddr=cpu.DDR_ba,
            io_DDR_CAS_n=cpu.DDR_cas_n,
            io_DDR_Clk_n=cpu.DDR_ck_n,
            io_DDR_Clk=cpu.DDR_ck_p,
            io_DDR_CKE=cpu.DDR_cke,
            io_DDR_CS_n=cpu.DDR_cs_n,
            io_DDR_DM=cpu.DDR_dm,
            io_DDR_DQ=cpu.DDR_dq,
            io_DDR_DQS_n=cpu.DDR_dqs_n,
            io_DDR_DQS=cpu.DDR_dqs_p,
            io_DDR_ODT=cpu.DDR_odt,
            io_DDR_RAS_n=cpu.DDR_ras_n,
            io_DDR_DRSTB=cpu.DDR_reset_n,
            io_DDR_WEB=cpu.DDR_we_n,
            io_DDR_VRN=cpu.ddr_vrn,
            io_DDR_VRP=cpu.ddr_vrp,
            o_FCLK_CLK0=self.fclk[0],
            o_FCLK_CLK1=self.fclk[1],
            o_FCLK_CLK2=self.fclk[2],
            o_FCLK_CLK3=self.fclk[3],
            o_FCLK_RESET0_N=self.frstn[0],
            o_FCLK_RESET1_N=self.frstn[1],
            o_FCLK_RESET2_N=self.frstn[2],
            o_FCLK_RESET3_N=self.frstn[3],
            i_M_AXI_GP0_ACLK=axi.aclk,
            o_M_AXI_GP0_ARVALID=axi.arvalid,
            o_M_AXI_GP0_AWVALID=axi.awvalid,
            o_M_AXI_GP0_BREADY=axi.bready,
            o_M_AXI_GP0_RREADY=axi.rready,
            o_M_AXI_GP0_WLAST=axi.wlast,
            o_M_AXI_GP0_WVALID=axi.wvalid,
            o_M_AXI_GP0_ARID=axi.arid,
            o_M_AXI_GP0_AWID=axi.awid,
            o_M_AXI_GP0_WID=axi.wid,
            o_M_AXI_GP0_ARBURST=axi.arburst,
            o_M_AXI_GP0_ARLOCK=axi.arlock,
            o_M_AXI_GP0_ARSIZE=axi.arsize,
            o_M_AXI_GP0_AWBURST=axi.awburst,
            o_M_AXI_GP0_AWLOCK=axi.awlock,
            o_M_AXI_GP0_AWSIZE=axi.awsize,
            o_M_AXI_GP0_ARPROT=axi.arprot,
            o_M_AXI_GP0_AWPROT=axi.awprot,
            o_M_AXI_GP0_ARADDR=axi.araddr,
            o_M_AXI_GP0_AWADDR=axi.awaddr,
            o_M_AXI_GP0_WDATA=axi.wdata,
            o_M_AXI_GP0_ARCACHE=axi.arcache,
            o_M_AXI_GP0_ARLEN=axi.arlen,
            o_M_AXI_GP0_ARQOS=axi.arqos,
            o_M_AXI_GP0_AWCACHE=axi.awcache,
            o_M_AXI_GP0_AWLEN=axi.awlen,
            o_M_AXI_GP0_AWQOS=axi.awqos,
            o_M_AXI_GP0_WSTRB=axi.wstrb,
            i_M_AXI_GP0_ARREADY=axi.arready,
            i_M_AXI_GP0_AWREADY=axi.awready,
            i_M_AXI_GP0_BVALID=axi.bvalid,
            i_M_AXI_GP0_RLAST=axi.rlast,
            i_M_AXI_GP0_RVALID=axi.rvalid,
            i_M_AXI_GP0_WREADY=axi.wready,
            i_M_AXI_GP0_BID=axi.bid,
            i_M_AXI_GP0_RID=axi.rid,
            i_M_AXI_GP0_BRESP=axi.bresp,
            i_M_AXI_GP0_RRESP=axi.rresp,
            i_M_AXI_GP0_RDATA=axi.rdata,
            i_SPI0_SS_I=0,
            # i_SPI0_SS_I=spi.ss_i,
            # o_SPI0_SS_O=spi.ss_o,
            # o_SPI0_SS_T=spi.ss_t,
            # o_SPI0_SS1_O=spi.ss1_o,
            # o_SPI0_SS2_O=spi.ss2_o,
            i_SPI0_SCLK_I=0,
            # i_SPI0_SCLK_I=spi.sclk_i,
            # o_SPI0_SCLK_O=spi.sclk_o,
            # o_SPI0_SCLK_T=spi.sclk_t,
            i_SPI0_MOSI_I=0,
            # i_SPI0_MOSI_I=spi.mosi_i,
            # o_SPI0_MOSI_O=spi.mosi_o,
            # o_SPI0_MOSI_T=spi.mosi_t,
            i_SPI0_MISO_I=0,
            # i_SPI0_MISO_I=spi.miso_i,
            # o_SPI0_MISO_O=spi.miso_o,
            # o_SPI0_MISO_T=spi.miso_t,
            i_USB0_VBUS_PWRFAULT=0,
        )


class Axi2Sys(Module):
    def __init__(self):
        self.sys = Record(sys_layout)
        self.axi = Record(axi_layout)

        ###

        self.comb += [self.sys.clk.eq(self.axi.aclk), self.sys.rstn.eq(self.axi.arstn)]

        self.specials += Instance(
            "axi_slave",
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
        cs = Signal(max=len(slaves))
        self.comb += cs.eq(master.addr[20:23])
        rets = []
        for i, s in enumerate(slaves):
            sel = Signal()
            self.comb += [
                sel.eq(cs == i),
                s.clk.eq(master.clk),
                s.rstn.eq(master.rstn),
                s.addr.eq(master.addr),
                s.wdata.eq(master.wdata),
                s.sel.eq(master.sel),
                s.wen.eq(sel & master.wen),
                s.ren.eq(sel & master.ren),
            ]
            ret = Cat(s.err, s.ack, s.rdata)
            rets.append(Replicate(sel, len(ret)) & ret)
        self.comb += Cat(master.err, master.ack, master.rdata).eq(reduce(or_, rets))


class Sys2Wishbone(Module):
    def __init__(self):
        self.wishbone = wb = wishbone.Interface()
        self.sys = sys = Record(sys_layout)

        ###

        sys2 = Record(sys_layout)

        self.specials += Instance(
            "bus_clk_bridge",
            i_sys_clk_i=sys.clk,
            i_sys_rstn_i=sys.rstn,
            i_sys_addr_i=sys.addr,
            i_sys_wdata_i=sys.wdata,
            i_sys_sel_i=sys.sel,
            i_sys_wen_i=sys.wen,
            i_sys_ren_i=sys.ren,
            o_sys_rdata_o=sys.rdata,
            o_sys_err_o=sys.err,
            o_sys_ack_o=sys.ack,
            i_clk_i=ClockSignal(),
            i_rstn_i=~ResetSignal(),
            o_addr_o=sys2.addr,
            o_wen_o=sys2.wen,
            o_ren_o=sys2.ren,
            o_wdata_o=sys2.wdata,
            i_rdata_i=sys2.rdata,
            i_err_i=sys2.err,
            i_ack_i=sys2.ack,
        )
        self.sync += [
            If(
                sys2.ren | sys2.wen,
                wb.cyc.eq(1),
                wb.adr.eq(sys2.addr[2:]),
                wb.we.eq(sys2.wen),
                wb.dat_w.eq(sys2.wdata),
            ).Elif(wb.ack, wb.cyc.eq(0))
        ]
        self.comb += [
            wb.stb.eq(wb.cyc),
            sys2.rdata.eq(wb.dat_r),
            sys2.ack.eq(wb.ack),
            sys2.err.eq(wb.err),
        ]


class SysCDC(Module):
    def __init__(self, cd_target="sys"):
        self.source = Record(sys_layout)
        self.target = Record(sys_layout)

        self.specials += Instance(
            "bus_clk_bridge",
            i_sys_clk_i=self.source.clk,
            i_sys_rstn_i=self.source.rstn,
            i_sys_addr_i=self.source.addr,
            i_sys_wdata_i=self.source.wdata,
            i_sys_sel_i=self.source.sel,
            i_sys_wen_i=self.source.wen,
            i_sys_ren_i=self.source.ren,
            o_sys_rdata_o=self.source.rdata,
            o_sys_err_o=self.source.err,
            o_sys_ack_o=self.source.ack,
            i_clk_i=self.target.clk,
            i_rstn_i=self.target.rstn,
            o_addr_o=self.target.addr,
            o_wdata_o=self.target.wdata,
            o_wen_o=self.target.wen,
            o_ren_o=self.target.ren,
            i_rdata_i=self.target.rdata,
            i_err_i=self.target.err,
            i_ack_i=self.target.ack,
        )
        self.comb += [
            self.target.clk.eq(ClockSignal(cd_target)),
            self.target.rstn.eq(~ResetSignal(cd_target)),
        ]


class Sys2CSR(Module):
    def __init__(self):
        self.csr = csr_bus.Interface()
        self.sys = Record(sys_layout)

        ###

        stb = Signal()
        self.sync += [
            stb.eq(self.sys.wen | self.sys.ren),
            self.csr.adr.eq(self.sys.addr[2:]),
            self.csr.we.eq(self.sys.wen),
            self.csr.dat_w.eq(self.sys.wdata),
            self.sys.ack.eq(stb),
            self.sys.rdata.eq(self.csr.dat_r),
        ]
