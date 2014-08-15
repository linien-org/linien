//Copyright 1986-2014 Xilinx, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2014.2 (lin64) Build 932637 Wed Jun 11 13:08:52 MDT 2014
//Date        : Fri Aug 15 00:51:38 2014
//Host        : 688rj1 running 64-bit Ubuntu 14.04 LTS
//Command     : generate_target system.bd
//Design      : system
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CORE_GENERATION_INFO = "system,IP_Integrator,{x_ipVendor=xilinx.com,x_ipLanguage=VERILOG,numBlks=1,numReposBlks=1,numNonXlnxBlks=0,numHierBlks=0,maxHierDepth=0,da_ps7_cnt=1}" *) 
module system
   (DDR_addr,
    DDR_ba,
    DDR_cas_n,
    DDR_ck_n,
    DDR_ck_p,
    DDR_cke,
    DDR_cs_n,
    DDR_dm,
    DDR_dq,
    DDR_dqs_n,
    DDR_dqs_p,
    DDR_odt,
    DDR_ras_n,
    DDR_reset_n,
    DDR_we_n,
    FCLK_CLK0,
    FCLK_CLK1,
    FCLK_CLK2,
    FCLK_CLK3,
    FCLK_RESET0_N,
    FCLK_RESET1_N,
    FCLK_RESET2_N,
    FCLK_RESET3_N,
    FIXED_IO_ddr_vrn,
    FIXED_IO_ddr_vrp,
    FIXED_IO_mio,
    FIXED_IO_ps_clk,
    FIXED_IO_ps_porb,
    FIXED_IO_ps_srstb,
    M_AXI_GP0_araddr,
    M_AXI_GP0_arburst,
    M_AXI_GP0_arcache,
    M_AXI_GP0_arid,
    M_AXI_GP0_arlen,
    M_AXI_GP0_arlock,
    M_AXI_GP0_arprot,
    M_AXI_GP0_arqos,
    M_AXI_GP0_arready,
    M_AXI_GP0_arsize,
    M_AXI_GP0_arvalid,
    M_AXI_GP0_awaddr,
    M_AXI_GP0_awburst,
    M_AXI_GP0_awcache,
    M_AXI_GP0_awid,
    M_AXI_GP0_awlen,
    M_AXI_GP0_awlock,
    M_AXI_GP0_awprot,
    M_AXI_GP0_awqos,
    M_AXI_GP0_awready,
    M_AXI_GP0_awsize,
    M_AXI_GP0_awvalid,
    M_AXI_GP0_bid,
    M_AXI_GP0_bready,
    M_AXI_GP0_bresp,
    M_AXI_GP0_bvalid,
    M_AXI_GP0_rdata,
    M_AXI_GP0_rid,
    M_AXI_GP0_rlast,
    M_AXI_GP0_rready,
    M_AXI_GP0_rresp,
    M_AXI_GP0_rvalid,
    M_AXI_GP0_wdata,
    M_AXI_GP0_wid,
    M_AXI_GP0_wlast,
    M_AXI_GP0_wready,
    M_AXI_GP0_wstrb,
    M_AXI_GP0_wvalid,
    SPI0_MISO_I,
    SPI0_MISO_O,
    SPI0_MISO_T,
    SPI0_MOSI_I,
    SPI0_MOSI_O,
    SPI0_MOSI_T,
    SPI0_SCLK_I,
    SPI0_SCLK_O,
    SPI0_SCLK_T,
    SPI0_SS1_O,
    SPI0_SS2_O,
    SPI0_SS_I,
    SPI0_SS_O,
    SPI0_SS_T);
  inout [14:0]DDR_addr;
  inout [2:0]DDR_ba;
  inout DDR_cas_n;
  inout DDR_ck_n;
  inout DDR_ck_p;
  inout DDR_cke;
  inout DDR_cs_n;
  inout [3:0]DDR_dm;
  inout [31:0]DDR_dq;
  inout [3:0]DDR_dqs_n;
  inout [3:0]DDR_dqs_p;
  inout DDR_odt;
  inout DDR_ras_n;
  inout DDR_reset_n;
  inout DDR_we_n;
  output FCLK_CLK0;
  output FCLK_CLK1;
  output FCLK_CLK2;
  output FCLK_CLK3;
  output FCLK_RESET0_N;
  output FCLK_RESET1_N;
  output FCLK_RESET2_N;
  output FCLK_RESET3_N;
  inout FIXED_IO_ddr_vrn;
  inout FIXED_IO_ddr_vrp;
  inout [53:0]FIXED_IO_mio;
  inout FIXED_IO_ps_clk;
  inout FIXED_IO_ps_porb;
  inout FIXED_IO_ps_srstb;
  output [31:0]M_AXI_GP0_araddr;
  output [1:0]M_AXI_GP0_arburst;
  output [3:0]M_AXI_GP0_arcache;
  output [11:0]M_AXI_GP0_arid;
  output [3:0]M_AXI_GP0_arlen;
  output [1:0]M_AXI_GP0_arlock;
  output [2:0]M_AXI_GP0_arprot;
  output [3:0]M_AXI_GP0_arqos;
  input M_AXI_GP0_arready;
  output [2:0]M_AXI_GP0_arsize;
  output M_AXI_GP0_arvalid;
  output [31:0]M_AXI_GP0_awaddr;
  output [1:0]M_AXI_GP0_awburst;
  output [3:0]M_AXI_GP0_awcache;
  output [11:0]M_AXI_GP0_awid;
  output [3:0]M_AXI_GP0_awlen;
  output [1:0]M_AXI_GP0_awlock;
  output [2:0]M_AXI_GP0_awprot;
  output [3:0]M_AXI_GP0_awqos;
  input M_AXI_GP0_awready;
  output [2:0]M_AXI_GP0_awsize;
  output M_AXI_GP0_awvalid;
  input [11:0]M_AXI_GP0_bid;
  output M_AXI_GP0_bready;
  input [1:0]M_AXI_GP0_bresp;
  input M_AXI_GP0_bvalid;
  input [31:0]M_AXI_GP0_rdata;
  input [11:0]M_AXI_GP0_rid;
  input M_AXI_GP0_rlast;
  output M_AXI_GP0_rready;
  input [1:0]M_AXI_GP0_rresp;
  input M_AXI_GP0_rvalid;
  output [31:0]M_AXI_GP0_wdata;
  output [11:0]M_AXI_GP0_wid;
  output M_AXI_GP0_wlast;
  input M_AXI_GP0_wready;
  output [3:0]M_AXI_GP0_wstrb;
  output M_AXI_GP0_wvalid;
  input SPI0_MISO_I;
  output SPI0_MISO_O;
  output SPI0_MISO_T;
  input SPI0_MOSI_I;
  output SPI0_MOSI_O;
  output SPI0_MOSI_T;
  input SPI0_SCLK_I;
  output SPI0_SCLK_O;
  output SPI0_SCLK_T;
  output SPI0_SS1_O;
  output SPI0_SS2_O;
  input SPI0_SS_I;
  output SPI0_SS_O;
  output SPI0_SS_T;

  wire GND_1;
  wire [14:0]processing_system7_0_ddr_ADDR;
  wire [2:0]processing_system7_0_ddr_BA;
  wire processing_system7_0_ddr_CAS_N;
  wire processing_system7_0_ddr_CKE;
  wire processing_system7_0_ddr_CK_N;
  wire processing_system7_0_ddr_CK_P;
  wire processing_system7_0_ddr_CS_N;
  wire [3:0]processing_system7_0_ddr_DM;
  wire [31:0]processing_system7_0_ddr_DQ;
  wire [3:0]processing_system7_0_ddr_DQS_N;
  wire [3:0]processing_system7_0_ddr_DQS_P;
  wire processing_system7_0_ddr_ODT;
  wire processing_system7_0_ddr_RAS_N;
  wire processing_system7_0_ddr_RESET_N;
  wire processing_system7_0_ddr_WE_N;
  wire processing_system7_0_fclk_clk0;
  wire processing_system7_0_fclk_clk1;
  wire processing_system7_0_fclk_clk2;
  wire processing_system7_0_fclk_clk3;
  wire processing_system7_0_fclk_reset0_n;
  wire processing_system7_0_fclk_reset1_n;
  wire processing_system7_0_fclk_reset2_n;
  wire processing_system7_0_fclk_reset3_n;
  wire processing_system7_0_fixed_io_DDR_VRN;
  wire processing_system7_0_fixed_io_DDR_VRP;
  wire [53:0]processing_system7_0_fixed_io_MIO;
  wire processing_system7_0_fixed_io_PS_CLK;
  wire processing_system7_0_fixed_io_PS_PORB;
  wire processing_system7_0_fixed_io_PS_SRSTB;
  wire [31:0]processing_system7_0_m_axi_gp0_ARADDR;
  wire [1:0]processing_system7_0_m_axi_gp0_ARBURST;
  wire [3:0]processing_system7_0_m_axi_gp0_ARCACHE;
  wire [11:0]processing_system7_0_m_axi_gp0_ARID;
  wire [3:0]processing_system7_0_m_axi_gp0_ARLEN;
  wire [1:0]processing_system7_0_m_axi_gp0_ARLOCK;
  wire [2:0]processing_system7_0_m_axi_gp0_ARPROT;
  wire [3:0]processing_system7_0_m_axi_gp0_ARQOS;
  wire processing_system7_0_m_axi_gp0_ARREADY;
  wire [2:0]processing_system7_0_m_axi_gp0_ARSIZE;
  wire processing_system7_0_m_axi_gp0_ARVALID;
  wire [31:0]processing_system7_0_m_axi_gp0_AWADDR;
  wire [1:0]processing_system7_0_m_axi_gp0_AWBURST;
  wire [3:0]processing_system7_0_m_axi_gp0_AWCACHE;
  wire [11:0]processing_system7_0_m_axi_gp0_AWID;
  wire [3:0]processing_system7_0_m_axi_gp0_AWLEN;
  wire [1:0]processing_system7_0_m_axi_gp0_AWLOCK;
  wire [2:0]processing_system7_0_m_axi_gp0_AWPROT;
  wire [3:0]processing_system7_0_m_axi_gp0_AWQOS;
  wire processing_system7_0_m_axi_gp0_AWREADY;
  wire [2:0]processing_system7_0_m_axi_gp0_AWSIZE;
  wire processing_system7_0_m_axi_gp0_AWVALID;
  wire [11:0]processing_system7_0_m_axi_gp0_BID;
  wire processing_system7_0_m_axi_gp0_BREADY;
  wire [1:0]processing_system7_0_m_axi_gp0_BRESP;
  wire processing_system7_0_m_axi_gp0_BVALID;
  wire [31:0]processing_system7_0_m_axi_gp0_RDATA;
  wire [11:0]processing_system7_0_m_axi_gp0_RID;
  wire processing_system7_0_m_axi_gp0_RLAST;
  wire processing_system7_0_m_axi_gp0_RREADY;
  wire [1:0]processing_system7_0_m_axi_gp0_RRESP;
  wire processing_system7_0_m_axi_gp0_RVALID;
  wire [31:0]processing_system7_0_m_axi_gp0_WDATA;
  wire [11:0]processing_system7_0_m_axi_gp0_WID;
  wire processing_system7_0_m_axi_gp0_WLAST;
  wire processing_system7_0_m_axi_gp0_WREADY;
  wire [3:0]processing_system7_0_m_axi_gp0_WSTRB;
  wire processing_system7_0_m_axi_gp0_WVALID;
  wire processing_system7_0_spi0_miso_o;
  wire processing_system7_0_spi0_miso_t;
  wire processing_system7_0_spi0_mosi_o;
  wire processing_system7_0_spi0_mosi_t;
  wire processing_system7_0_spi0_sclk_o;
  wire processing_system7_0_spi0_sclk_t;
  wire processing_system7_0_spi0_ss1_o;
  wire processing_system7_0_spi0_ss2_o;
  wire processing_system7_0_spi0_ss_o;
  wire processing_system7_0_spi0_ss_t;
  wire spi0_miso_i_1;
  wire spi0_mosi_i_1;
  wire spi0_sclk_i_1;
  wire spi0_ss_i_1;

  assign FCLK_CLK0 = processing_system7_0_fclk_clk0;
  assign FCLK_CLK1 = processing_system7_0_fclk_clk1;
  assign FCLK_CLK2 = processing_system7_0_fclk_clk2;
  assign FCLK_CLK3 = processing_system7_0_fclk_clk3;
  assign FCLK_RESET0_N = processing_system7_0_fclk_reset0_n;
  assign FCLK_RESET1_N = processing_system7_0_fclk_reset1_n;
  assign FCLK_RESET2_N = processing_system7_0_fclk_reset2_n;
  assign FCLK_RESET3_N = processing_system7_0_fclk_reset3_n;
  assign M_AXI_GP0_araddr[31:0] = processing_system7_0_m_axi_gp0_ARADDR;
  assign M_AXI_GP0_arburst[1:0] = processing_system7_0_m_axi_gp0_ARBURST;
  assign M_AXI_GP0_arcache[3:0] = processing_system7_0_m_axi_gp0_ARCACHE;
  assign M_AXI_GP0_arid[11:0] = processing_system7_0_m_axi_gp0_ARID;
  assign M_AXI_GP0_arlen[3:0] = processing_system7_0_m_axi_gp0_ARLEN;
  assign M_AXI_GP0_arlock[1:0] = processing_system7_0_m_axi_gp0_ARLOCK;
  assign M_AXI_GP0_arprot[2:0] = processing_system7_0_m_axi_gp0_ARPROT;
  assign M_AXI_GP0_arqos[3:0] = processing_system7_0_m_axi_gp0_ARQOS;
  assign M_AXI_GP0_arsize[2:0] = processing_system7_0_m_axi_gp0_ARSIZE;
  assign M_AXI_GP0_arvalid = processing_system7_0_m_axi_gp0_ARVALID;
  assign M_AXI_GP0_awaddr[31:0] = processing_system7_0_m_axi_gp0_AWADDR;
  assign M_AXI_GP0_awburst[1:0] = processing_system7_0_m_axi_gp0_AWBURST;
  assign M_AXI_GP0_awcache[3:0] = processing_system7_0_m_axi_gp0_AWCACHE;
  assign M_AXI_GP0_awid[11:0] = processing_system7_0_m_axi_gp0_AWID;
  assign M_AXI_GP0_awlen[3:0] = processing_system7_0_m_axi_gp0_AWLEN;
  assign M_AXI_GP0_awlock[1:0] = processing_system7_0_m_axi_gp0_AWLOCK;
  assign M_AXI_GP0_awprot[2:0] = processing_system7_0_m_axi_gp0_AWPROT;
  assign M_AXI_GP0_awqos[3:0] = processing_system7_0_m_axi_gp0_AWQOS;
  assign M_AXI_GP0_awsize[2:0] = processing_system7_0_m_axi_gp0_AWSIZE;
  assign M_AXI_GP0_awvalid = processing_system7_0_m_axi_gp0_AWVALID;
  assign M_AXI_GP0_bready = processing_system7_0_m_axi_gp0_BREADY;
  assign M_AXI_GP0_rready = processing_system7_0_m_axi_gp0_RREADY;
  assign M_AXI_GP0_wdata[31:0] = processing_system7_0_m_axi_gp0_WDATA;
  assign M_AXI_GP0_wid[11:0] = processing_system7_0_m_axi_gp0_WID;
  assign M_AXI_GP0_wlast = processing_system7_0_m_axi_gp0_WLAST;
  assign M_AXI_GP0_wstrb[3:0] = processing_system7_0_m_axi_gp0_WSTRB;
  assign M_AXI_GP0_wvalid = processing_system7_0_m_axi_gp0_WVALID;
  assign SPI0_MISO_O = processing_system7_0_spi0_miso_o;
  assign SPI0_MISO_T = processing_system7_0_spi0_miso_t;
  assign SPI0_MOSI_O = processing_system7_0_spi0_mosi_o;
  assign SPI0_MOSI_T = processing_system7_0_spi0_mosi_t;
  assign SPI0_SCLK_O = processing_system7_0_spi0_sclk_o;
  assign SPI0_SCLK_T = processing_system7_0_spi0_sclk_t;
  assign SPI0_SS1_O = processing_system7_0_spi0_ss1_o;
  assign SPI0_SS2_O = processing_system7_0_spi0_ss2_o;
  assign SPI0_SS_O = processing_system7_0_spi0_ss_o;
  assign SPI0_SS_T = processing_system7_0_spi0_ss_t;
  assign processing_system7_0_m_axi_gp0_ARREADY = M_AXI_GP0_arready;
  assign processing_system7_0_m_axi_gp0_AWREADY = M_AXI_GP0_awready;
  assign processing_system7_0_m_axi_gp0_BID = M_AXI_GP0_bid[11:0];
  assign processing_system7_0_m_axi_gp0_BRESP = M_AXI_GP0_bresp[1:0];
  assign processing_system7_0_m_axi_gp0_BVALID = M_AXI_GP0_bvalid;
  assign processing_system7_0_m_axi_gp0_RDATA = M_AXI_GP0_rdata[31:0];
  assign processing_system7_0_m_axi_gp0_RID = M_AXI_GP0_rid[11:0];
  assign processing_system7_0_m_axi_gp0_RLAST = M_AXI_GP0_rlast;
  assign processing_system7_0_m_axi_gp0_RRESP = M_AXI_GP0_rresp[1:0];
  assign processing_system7_0_m_axi_gp0_RVALID = M_AXI_GP0_rvalid;
  assign processing_system7_0_m_axi_gp0_WREADY = M_AXI_GP0_wready;
  assign spi0_miso_i_1 = SPI0_MISO_I;
  assign spi0_mosi_i_1 = SPI0_MOSI_I;
  assign spi0_sclk_i_1 = SPI0_SCLK_I;
  assign spi0_ss_i_1 = SPI0_SS_I;
GND GND
       (.G(GND_1));
system_processing_system7_0_0 processing_system7_0
       (.DDR_Addr(DDR_addr[14:0]),
        .DDR_BankAddr(DDR_ba[2:0]),
        .DDR_CAS_n(DDR_cas_n),
        .DDR_CKE(DDR_cke),
        .DDR_CS_n(DDR_cs_n),
        .DDR_Clk(DDR_ck_p),
        .DDR_Clk_n(DDR_ck_n),
        .DDR_DM(DDR_dm[3:0]),
        .DDR_DQ(DDR_dq[31:0]),
        .DDR_DQS(DDR_dqs_p[3:0]),
        .DDR_DQS_n(DDR_dqs_n[3:0]),
        .DDR_DRSTB(DDR_reset_n),
        .DDR_ODT(DDR_odt),
        .DDR_RAS_n(DDR_ras_n),
        .DDR_VRN(FIXED_IO_ddr_vrn),
        .DDR_VRP(FIXED_IO_ddr_vrp),
        .DDR_WEB(DDR_we_n),
        .FCLK_CLK0(processing_system7_0_fclk_clk0),
        .FCLK_CLK1(processing_system7_0_fclk_clk1),
        .FCLK_CLK2(processing_system7_0_fclk_clk2),
        .FCLK_CLK3(processing_system7_0_fclk_clk3),
        .FCLK_RESET0_N(processing_system7_0_fclk_reset0_n),
        .FCLK_RESET1_N(processing_system7_0_fclk_reset1_n),
        .FCLK_RESET2_N(processing_system7_0_fclk_reset2_n),
        .FCLK_RESET3_N(processing_system7_0_fclk_reset3_n),
        .MIO(FIXED_IO_mio[53:0]),
        .M_AXI_GP0_ACLK(processing_system7_0_fclk_clk0),
        .M_AXI_GP0_ARADDR(processing_system7_0_m_axi_gp0_ARADDR),
        .M_AXI_GP0_ARBURST(processing_system7_0_m_axi_gp0_ARBURST),
        .M_AXI_GP0_ARCACHE(processing_system7_0_m_axi_gp0_ARCACHE),
        .M_AXI_GP0_ARID(processing_system7_0_m_axi_gp0_ARID),
        .M_AXI_GP0_ARLEN(processing_system7_0_m_axi_gp0_ARLEN),
        .M_AXI_GP0_ARLOCK(processing_system7_0_m_axi_gp0_ARLOCK),
        .M_AXI_GP0_ARPROT(processing_system7_0_m_axi_gp0_ARPROT),
        .M_AXI_GP0_ARQOS(processing_system7_0_m_axi_gp0_ARQOS),
        .M_AXI_GP0_ARREADY(processing_system7_0_m_axi_gp0_ARREADY),
        .M_AXI_GP0_ARSIZE(processing_system7_0_m_axi_gp0_ARSIZE),
        .M_AXI_GP0_ARVALID(processing_system7_0_m_axi_gp0_ARVALID),
        .M_AXI_GP0_AWADDR(processing_system7_0_m_axi_gp0_AWADDR),
        .M_AXI_GP0_AWBURST(processing_system7_0_m_axi_gp0_AWBURST),
        .M_AXI_GP0_AWCACHE(processing_system7_0_m_axi_gp0_AWCACHE),
        .M_AXI_GP0_AWID(processing_system7_0_m_axi_gp0_AWID),
        .M_AXI_GP0_AWLEN(processing_system7_0_m_axi_gp0_AWLEN),
        .M_AXI_GP0_AWLOCK(processing_system7_0_m_axi_gp0_AWLOCK),
        .M_AXI_GP0_AWPROT(processing_system7_0_m_axi_gp0_AWPROT),
        .M_AXI_GP0_AWQOS(processing_system7_0_m_axi_gp0_AWQOS),
        .M_AXI_GP0_AWREADY(processing_system7_0_m_axi_gp0_AWREADY),
        .M_AXI_GP0_AWSIZE(processing_system7_0_m_axi_gp0_AWSIZE),
        .M_AXI_GP0_AWVALID(processing_system7_0_m_axi_gp0_AWVALID),
        .M_AXI_GP0_BID(processing_system7_0_m_axi_gp0_BID),
        .M_AXI_GP0_BREADY(processing_system7_0_m_axi_gp0_BREADY),
        .M_AXI_GP0_BRESP(processing_system7_0_m_axi_gp0_BRESP),
        .M_AXI_GP0_BVALID(processing_system7_0_m_axi_gp0_BVALID),
        .M_AXI_GP0_RDATA(processing_system7_0_m_axi_gp0_RDATA),
        .M_AXI_GP0_RID(processing_system7_0_m_axi_gp0_RID),
        .M_AXI_GP0_RLAST(processing_system7_0_m_axi_gp0_RLAST),
        .M_AXI_GP0_RREADY(processing_system7_0_m_axi_gp0_RREADY),
        .M_AXI_GP0_RRESP(processing_system7_0_m_axi_gp0_RRESP),
        .M_AXI_GP0_RVALID(processing_system7_0_m_axi_gp0_RVALID),
        .M_AXI_GP0_WDATA(processing_system7_0_m_axi_gp0_WDATA),
        .M_AXI_GP0_WID(processing_system7_0_m_axi_gp0_WID),
        .M_AXI_GP0_WLAST(processing_system7_0_m_axi_gp0_WLAST),
        .M_AXI_GP0_WREADY(processing_system7_0_m_axi_gp0_WREADY),
        .M_AXI_GP0_WSTRB(processing_system7_0_m_axi_gp0_WSTRB),
        .M_AXI_GP0_WVALID(processing_system7_0_m_axi_gp0_WVALID),
        .PS_CLK(FIXED_IO_ps_clk),
        .PS_PORB(FIXED_IO_ps_porb),
        .PS_SRSTB(FIXED_IO_ps_srstb),
        .SPI0_MISO_I(spi0_miso_i_1),
        .SPI0_MISO_O(processing_system7_0_spi0_miso_o),
        .SPI0_MISO_T(processing_system7_0_spi0_miso_t),
        .SPI0_MOSI_I(spi0_mosi_i_1),
        .SPI0_MOSI_O(processing_system7_0_spi0_mosi_o),
        .SPI0_MOSI_T(processing_system7_0_spi0_mosi_t),
        .SPI0_SCLK_I(spi0_sclk_i_1),
        .SPI0_SCLK_O(processing_system7_0_spi0_sclk_o),
        .SPI0_SCLK_T(processing_system7_0_spi0_sclk_t),
        .SPI0_SS1_O(processing_system7_0_spi0_ss1_o),
        .SPI0_SS2_O(processing_system7_0_spi0_ss2_o),
        .SPI0_SS_I(spi0_ss_i_1),
        .SPI0_SS_O(processing_system7_0_spi0_ss_o),
        .SPI0_SS_T(processing_system7_0_spi0_ss_t),
        .USB0_VBUS_PWRFAULT(GND_1));
endmodule
