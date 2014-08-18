# Robert Jordens <jordens@gmail.com> 2014

from collections import OrderedDict

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bus import wishbone2csr, csr, wishbone
from migen.bank import csrgen
from migen.bank.description import *
from migen.fhdl.bitcontainer import bits_for
from migen.genlib.cordic import Cordic

from .iir import Iir
from .limit import Limit


signal_width = 25
coeff_width = 18

ports_layout = [
        ("i", (signal_width, True)),
        ("o", (signal_width, True)),
]


class Sweep(Module):
    def __init__(self):
        self.o = Signal((signal_width, True))


class InOut(Module, AutoCSR):
    def __init__(self, i, o):
        self.ports = Record(ports_layout)

        self._in_min = CSRStorage(signal_width)
        self._in_max = CSRStorage(signal_width)
        self._in_shift = CSRStorage(signal_width)
        self._in_val = CSRStatus(signal_width)
        self._in_low = CSRStatus()
        self._in_high = CSRStatus()

        self._demod = CSRStorage()
        self._demod_amp = CSRStorage(signal_width)
        self._demod_phase = CSRStorage(signal_width)

        self._mod = CSRStorage()
        self._mod_amp = CSRStorage(signal_width)
        self._mod_freq = CSRStorage(32)

        self._sweep = CSRStorage()
        self._sweep_amp = CSRStorage(signal_width)
        self._sweep_offset = CSRStorage(signal_width)
        self._sweep_freq = CSRStorage(signal_width)

        self._out_min = CSRStorage(signal_width)
        self._out_max = CSRStorage(signal_width)
        self._out_shift = CSRStorage(signal_width)
        self._out_val = CSRStatus(signal_width)
        self._out_low = CSRStatus()
        self._out_high = CSRStatus()

        ###

        #self.submodules.mod = Cordic(width=signal_width, guard=None)
        #self.submodules.demod = Cordic(width=signal_width, guard=None)
        self.submodules.sweep = Sweep()
        self.submodules.limit = Limit()
        mod_phase = Signal(32)
        demod_phase = Signal(32)

        self.sync += [
                mod_phase.eq(mod_phase + self._mod_freq.storage),
                demod_phase.eq(mod_phase + self._demod_phase.storage),
        ]

        self.comb += [
                #self.mod.xi.eq(self._mod_amp.storage),
                #self.mod.zi.eq(mod_phase),
                #self.demod.xi.eq(i),
                #self.demod.zi.eq(demod_phase),
                #self.ports.o.eq(Mux(self._demod.storage, self.demod.xo, i)),
                self.ports.o.eq(i),
                self.limit.x.eq(self.ports.i
                    #+ Mux(self._mod.storage, self.mod.xo, 0)
                    #+ Mux(self._sweep.storage, self.sweep.o, 0)
                ),
                o.eq(self.limit.y),
        ]


class IIR1(Module, AutoCSR):
    def __init__(self):
        self.ports = Record(ports_layout)
        self.submodules.m = Iir(signal_width=flen(self.ports.i), coeff_width=coeff_width,
                order=1)
        self.sync += self.ports.o.eq(self.m.y), self.m.x.eq(self.ports.i)


class IIR2(Module, AutoCSR):
    def __init__(self):
        self.ports = Record(ports_layout)
        self.submodules.m = Iir(signal_width=flen(self.ports.i), coeff_width=coeff_width,
                order=2)
        self.sync += self.ports.o.eq(self.m.y), self.m.x.eq(self.ports.i)


class FilterMux(Module, AutoCSR):
    def __init__(self, parts):
        outs = Array([part.ports.o for part in parts])

        for i, part in enumerate(parts):
            m = CSRStorage(bits_for(len(parts)))
            setattr(self, "_mux%i" % i, m)
            self.sync += part.ports.i.eq(outs[m.storage])


class Pitaya2Wishbone(Module):
    def __init__(self, sys):
        self.wishbone = wb = wishbone.Interface()

        ###

        adr = Signal.like(sys.addr_i)

        self.specials += Instance("bus_clk_bridge",
                i_sys_clk_i=sys.clk_i, i_sys_rstn_i=sys.rstn_i,
                i_sys_addr_i=sys.addr_i, i_sys_wdata_i=sys.wdata_i,
                i_sys_sel_i=sys.sel_i, i_sys_wen_i=sys.wen_i,
                i_sys_ren_i=sys.ren_i, o_sys_rdata_o=sys.rdata_o,
                o_sys_err_o=sys.err_o, o_sys_ack_o=sys.ack_o,
                i_clk_i=ClockSignal(), i_rstn_i=ResetSignal(),
                o_addr_o=adr, o_wdata_o=wb.dat_w, o_wen_o=wb.we,
                o_ren_o=wb.stb, i_rdata_i=wb.dat_r, i_err_i=wb.err,
                i_ack_i=wb.ack,
        )

        self.comb += [
                wb.cyc.eq(wb.stb),
                wb.adr.eq(adr[2:]),
        ]


class Pid(Module):
    def __init__(self):
        self.ins = [Signal((14, True)) for i in range(2)]
        self.outs = [Signal((14, True)) for i in range(2)]
        parts = OrderedDict(
                io_a=InOut(self.ins[0], self.outs[0]), 
                io_b=InOut(self.ins[1], self.outs[1]), 
                iir1_a=IIR1(),
                #iir1_b=IIR1(), iir1_c=IIR1(), iir1_d=IIR1(),
                #iir2_a=IIR2(), iir2_b=IIR2(), iir2_c=IIR2(), iir2_d=IIR2(),
        )
        self.submodules.mux = FilterMux(parts.values())
        self.csr_map = {"mux": 31}
        for i, (k, v) in enumerate(parts.items()):
            setattr(self.submodules, k, v)
            self.csr_map[k] = i

        self.submodules.csrbanks = csrgen.BankArray(self,
                    lambda name, mem: self.csr_map[name if mem is None
                        else name + "_" + mem.name_override])
        self.submodules.wb2csr = wishbone2csr.WB2CSR()
        self.submodules.csrcon = csr.Interconnect(self.wb2csr.csr,
                self.csrbanks.get_buses())
        self.wishbone = self.wb2csr.wishbone


class RedPid(Module):
    def __init__(self):
        clk_i = Signal()
        rstn_i = Signal()
        self.ios = {clk_i, rstn_i}

        dat = Record([
            ("a_i", 14),
            ("b_i", 14),
            ("a_o", 14),
            ("b_o", 14),
        ])
        self.ios |= set(dat.flatten())

        sys = Record([
            ("rstn_i", 1),
            ("clk_i", 1),
            ("addr_i", 32),
            ("wdata_i", 32),
            ("sel_i", 4),
            ("wen_i", 1),
            ("ren_i", 1),
            ("rdata_o", 32),
            ("err_o", 1),
            ("ack_o", 1),
        ])
        self.ios |= set(sys.flatten())

        ###

        self.clock_domains.cd_sys = ClockDomain()
        self.comb += [
                self.cd_sys.clk.eq(clk_i),
                self.cd_sys.rst.eq(~rstn_i),
        ]
        self.submodules.pid = Pid()
        self.comb += [
                self.pid.ins[0].eq(dat.a_i),
                self.pid.ins[1].eq(dat.b_i),
                dat.a_o.eq(self.pid.outs[0]),
                dat.b_o.eq(self.pid.outs[1]),
        ]
        self.submodules.pitaya = Pitaya2Wishbone(sys)
        self.submodules.wbcon = wishbone.InterconnectPointToPoint(
                self.pitaya.wishbone, self.pid.wishbone)


if __name__ == "__main__":
    from migen.fhdl import verilog
    redpid = RedPid()
    v = verilog.convert(redpid, name="redpid", ios=redpid.ios)
    open("redpid.v", "w").write(v)
    #print(v)
