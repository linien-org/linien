# Copyright 2014-2015 Robert Jordens <jordens@gmail.com>
#
# This file is part of redpid.
#
# redpid is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# redpid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with redpid.  If not, see <http://www.gnu.org/licenses/>.

from migen import *
from misoc.interconnect import csr_bus
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage

# https://github.com/RedPitaya/RedPitaya/blob/master/FPGA/release1/fpga/code/rtl/red_pitaya_daisy.v

from .pitaya_ps import SysCDC, Sys2CSR, SysInterconnect, PitayaPS, sys_layout
from .crg import CRG
from .analog import PitayaAnalog
from .chains import FastChain, SlowChain, cross_connect
from .gpio import Gpio
from .xadc import XADC
from .delta_sigma import DeltaSigma
from .dna import DNA
from .lfsr import XORSHIFTGen
from .modulate import Modulate
from .sweep import SweepCSR
from .limit import LimitCSR
from .pid import PID
from .decimation import Decimate

from linien.common import ANALOG_OUT0


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
        adc_b = Signal((width, True))
        dac_a = Signal((width, True))
        dac_b = Signal((width, True))

        self.signal_in = adc_a, adc_b
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

        self.specials.asg = Instance("red_pitaya_asg",
                o_dac_a_o=asg_a,
                o_dac_b_o=asg_b,
                i_dac_clk_i=ClockSignal(),
                i_dac_rstn_i=~ResetSignal(),
                i_trig_a_i=self.gpio_trigger,
                i_trig_b_i=self.gpio_trigger,
                o_trig_out_o=asg_trig,

                i_sys_clk_i=self.asg_sys.clk,
                i_sys_rstn_i=self.asg_sys.rstn,
                i_sys_addr_i=self.asg_sys.addr,
                i_sys_wdata_i=self.asg_sys.wdata,
                i_sys_sel_i=self.asg_sys.sel,
                i_sys_wen_i=self.asg_sys.wen,
                i_sys_ren_i=self.asg_sys.ren,
                o_sys_rdata_o=self.asg_sys.rdata,
                o_sys_err_o=self.asg_sys.err,
                o_sys_ack_o=self.asg_sys.ack,
        )


class PIDCSR(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25, chain_factor_width=8):
        combined_error_signal = Signal((signal_width, True))
        self.control_signal = Signal((signal_width, True))

        s = signal_width - width

        factor_reset = 1 << (chain_factor_width - 1)
        # we use chain_factor_width + 1 for the single channel mode
        self.chain_a_factor = CSRStorage(chain_factor_width + 1, reset=factor_reset)
        self.chain_b_factor = CSRStorage(chain_factor_width + 1, reset=factor_reset)

        self.chain_a_offset = CSRStorage(width)
        self.chain_b_offset = CSRStorage(width)
        self.chain_a_offset_signed = Signal((width, True))
        self.chain_b_offset_signed = Signal((width, True))
        self.combined_offset = CSRStorage(width)
        self.combined_offset_signed = Signal((width, True))
        self.out_offset = CSRStorage(width)
        self.out_offset_signed = Signal((width, True))

        self.mod_channel = CSRStorage(1)
        self.control_channel = CSRStorage(1)
        self.sweep_channel = CSRStorage(2)

        self.sync += [
            self.chain_a_offset_signed.eq(self.chain_a_offset.storage),
            self.chain_b_offset_signed.eq(self.chain_b_offset.storage),
            self.combined_offset_signed.eq(self.combined_offset.storage),
            self.out_offset_signed.eq(self.out_offset.storage)
        ]

        self.state_in = []
        self.signal_in = []
        self.state_out = []
        self.signal_out = [
            self.control_signal, combined_error_signal
        ]

        self.slow_value = CSRStatus(width)

        self.submodules.mod = Modulate(width=width)
        self.submodules.sweep = SweepCSR(width=width, step_width=24, step_shift=18)
        self.submodules.limit_error_signal = LimitCSR(width=width, guard=4)
        self.submodules.limit_fast1 = LimitCSR(width=width, guard=5)
        self.submodules.limit_fast2 = LimitCSR(width=width, guard=5)
        self.submodules.pid = PID()

        max_decimation = 16
        self.slow_decimation = CSRStorage(bits_for(max_decimation))

        self.comb += [
            self.sweep.clear.eq(0),
            self.sweep.hold.eq(0),
        ]

        self.sync += [
            combined_error_signal.eq(self.limit_error_signal.y << s),
            self.control_signal.eq(Array([
                self.limit_fast1.y,
                self.limit_fast2.y
            ])[self.control_channel.storage] << s),
        ]


class Pid(Module, AutoCSR):
    def __init__(self, platform):
        csr_map = {
                "dna": 28, "xadc": 29, "gpio_n": 30, "gpio_p": 31,
                "fast_a": 0, "fast_b": 1,
                "slow": 2,
                #"slow_a": 2, "slow_b": 3, "slow_c": 4, "slow_d": 5,
                "scopegen": 6, "noise": 7, 'root': 8
        }

        chain_factor_bits = 8

        self.submodules.root = PIDCSR(chain_factor_width=chain_factor_bits)

        self.submodules.analog = PitayaAnalog(
                platform.request("adc"), platform.request("dac"))

        self.submodules.xadc = XADC(platform.request("xadc"))

        sys_double = ClockDomainsRenamer("sys_double")

        for i in range(4):
            pwm = platform.request("pwm", i)
            ds = sys_double(DeltaSigma(width=15))
            self.comb += pwm.eq(ds.out)
            setattr(self.submodules, "ds%i" % i, ds)

        exp = platform.request("exp")
        self.submodules.gpio_n = Gpio(exp.n)
        self.submodules.gpio_p = Gpio(exp.p)

        leds = Cat(*(platform.request("user_led", i) for i in range(8)))
        self.comb += leds.eq(self.gpio_n.o)

        self.submodules.dna = DNA(version=2)

        signal_width, coeff_width = 25, 18
        width = 14
        s = signal_width - width

        self.submodules.fast_a = FastChain(width, signal_width, coeff_width, self.root.mod, offset_signal=self.root.chain_a_offset_signed)
        self.submodules.fast_b = FastChain(width, signal_width, coeff_width, self.root.mod, offset_signal=self.root.chain_b_offset_signed)

        sys_slow = ClockDomainsRenamer("sys_slow")
        sys_double = ClockDomainsRenamer("sys_double")
        max_decimation = 16
        self.submodules.decimate = sys_double(Decimate(max_decimation))
        self.clock_domains.cd_decimated_clock = ClockDomain()
        decimated_clock = ClockDomainsRenamer('decimated_clock')
        self.submodules.slow = decimated_clock(SlowChain())

        self.submodules.scopegen = ScopeGen(signal_width)

        self.state_names, self.signal_names = cross_connect(self.gpio_n, [
            ("fast_a", self.fast_a), ("fast_b", self.fast_b),
            ("slow", self.slow), ("scopegen", self.scopegen),
            ("root", self.root)
        ])

        # now, we combine the output of the two paths, with a variable
        # factor each.
        mixed = Signal((2 + ((width + 1) + self.root.chain_a_factor.size), True))
        self.sync += mixed.eq(
            (
                # FIXME: wenn dual_channel an ist und und z.B. beide Werte auf 128
                # sind, geht damit jeweils ein bit verloren. Nicht schlimm,
                # vermutlich, aber eventuell kann man die weitere Kette mit
                # mehr Bits rechnen lassen?
                (self.root.chain_a_factor.storage * self.fast_a.dac)
                + (self.root.chain_b_factor.storage * self.fast_b.dac)
                + (self.root.combined_offset_signed << chain_factor_bits)
            )
        )

        mixed_limited = Signal((width, True))
        self.comb += [
            self.root.limit_error_signal.x.eq(mixed >> chain_factor_bits),
            mixed_limited.eq(self.root.limit_error_signal.y)
        ]

        pid_out = Signal((width, True))
        self.comb += [
            self.root.pid.input.eq(mixed_limited),
            pid_out.eq(self.root.pid.pid_out)
        ]

        fast_outs = list(Signal((width + 4, True)) for channel in (0, 1))

        for channel, fast_out in enumerate(fast_outs):
            self.sync += fast_out.eq(
                Mux(self.root.control_channel.storage == channel, pid_out, 0)
                + Mux(self.root.mod_channel.storage == channel, self.root.mod.y, 0)
                + Mux(self.root.sweep_channel.storage == channel, self.root.sweep.y, 0)
                + Mux(self.root.sweep_channel.storage == channel, self.root.out_offset_signed, 0)
            )

        slow_pid_out = Signal((width, True))
        self.comb += slow_pid_out.eq(self.slow.output)
        slow_out = Signal((width + 2, True))
        self.sync += slow_out.eq(
            slow_pid_out
            + Mux(self.root.sweep_channel.storage == ANALOG_OUT0, self.root.sweep.y, 0)
            + Mux(self.root.sweep_channel.storage == ANALOG_OUT0, self.root.out_offset_signed, 0)
        )
        slow_out_shifted = Signal(15)
        self.sync += slow_out_shifted.eq(
            # ds0 apparently has 16 bit, but only allowing positive
            # values --> "15 bit"?
            (self.slow.limit.y << 1) + (1<<14)
        )

        self.comb += [
                self.scopegen.gpio_trigger.eq(self.gpio_p.i[0]),
                self.scopegen.sweep_trigger.eq(self.root.sweep.sweep.trigger),

                self.fast_a.adc.eq(self.analog.adc_a),
                self.fast_b.adc.eq(self.analog.adc_b),

                self.root.limit_fast1.x.eq(fast_outs[0]),
                self.root.limit_fast2.x.eq(fast_outs[1]),

                self.analog.dac_a.eq(self.root.limit_fast1.y),
                self.analog.dac_b.eq(self.root.limit_fast2.y),

                # SLOW OUT
                self.slow.input.eq(self.root.control_signal >> s),
                self.decimate.decimation.eq(self.root.slow_decimation.storage),
                self.cd_decimated_clock.clk.eq(self.decimate.output),
                self.slow.limit.x.eq(slow_out),
                self.ds0.data.eq(slow_out_shifted),
                self.root.slow_value.status.eq(self.slow.limit.y),

                #self.slow_b.adc.eq(self.xadc.adc[1] << 4),
                #self.ds1.data.eq(self.slow_b.dac),
                #self.slow_c.adc.eq(self.xadc.adc[2] << 4),
                #self.ds2.data.eq(self.slow_c.dac),
                #self.slow_d.adc.eq(self.xadc.adc[3] << 4),
                #self.ds3.data.eq(self.slow_d.dac),
        ]

        self.submodules.csrbanks = csr_bus.CSRBankArray(self,
                    lambda name, mem: csr_map[name if mem is None
                        else name + "_" + mem.name_override])
        self.submodules.sys2csr = Sys2CSR()
        self.submodules.csrcon = csr_bus.Interconnect(self.sys2csr.csr,
                self.csrbanks.get_buses())
        self.submodules.syscdc = SysCDC()
        self.comb += self.syscdc.target.connect(self.sys2csr.sys)


class DummyID(Module, AutoCSR):
    def __init__(self):
        self.id = CSRStatus(1, reset=1)


class DummyHK(Module, AutoCSR):
    def __init__(self):
        self.submodules.id = DummyID()
        self.submodules.csrbanks = csr_bus.CSRBankArray(self,
                    lambda name, mem: 0)
        self.submodules.sys2csr = Sys2CSR()
        self.submodules.csrcon = csr_bus.Interconnect(self.sys2csr.csr,
                self.csrbanks.get_buses())
        self.sys = self.sys2csr.sys


class RedPid(Module):
    def __init__(self, platform):
        self.submodules.ps = PitayaPS(platform.request("cpu"))
        self.submodules.crg = CRG(platform.request("clk125"),
                self.ps.fclk[0], ~self.ps.frstn[0])
        self.submodules.pid = Pid(platform)

        self.submodules.hk = ClockDomainsRenamer("sys_ps")(DummyHK())

        self.submodules.ic = SysInterconnect(self.ps.axi.sys,
                self.hk.sys, self.pid.scopegen.scope_sys,
                self.pid.scopegen.asg_sys,
                self.pid.syscdc.source)
