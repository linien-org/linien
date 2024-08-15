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

from linien_common.common import OutputChannel
from migen import (
    Array,
    Cat,
    ClockDomain,
    ClockDomainsRenamer,
    If,
    Module,
    Mux,
    Signal,
    bits_for,
)
from misoc.interconnect import csr_bus
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage

from .logic.autolock import FPGAAutolock
from .logic.chains import FastChain, SlowChain, cross_connect
from .logic.decimation import Decimate
from .logic.delta_sigma import DeltaSigma
from .logic.iir import Iir
from .logic.limit import LimitCSR
from .logic.modulate import Modulate
from .logic.pid import PID
from .logic.sweep import SweepCSR
from .lowlevel.analog import PitayaAnalog
from .lowlevel.crg import CRG
from .lowlevel.dna import DNA
from .lowlevel.gpio import Gpio
from .lowlevel.pitaya_ps import PitayaPS, Sys2CSR, SysCDC, SysInterconnect
from .lowlevel.scopegen import ScopeGen
from .lowlevel.xadc import XADC


class LinienLogic(Module, AutoCSR):
    def __init__(self, width=14, signal_width=25, chain_factor_width=8, coeff_width=25):
        self.init_csr(width, chain_factor_width)
        self.init_submodules(width, signal_width)
        self.connect_pid()
        self.connect_everything(width, signal_width, coeff_width)

    def init_csr(self, width, chain_factor_width):
        self.dual_channel = CSRStorage(1)
        self.mod_channel = CSRStorage(1)
        self.control_channel = CSRStorage(1)
        self.sweep_channel = CSRStorage(2)
        self.slow_control_channel = CSRStorage(2)
        self.pid_only_mode = CSRStorage(1)

        # we use chain_factor_width + 1 for the single channel mode
        factor_reset = 1 << (chain_factor_width - 1)
        self.chain_a_factor = CSRStorage(chain_factor_width + 1, reset=factor_reset)
        self.chain_b_factor = CSRStorage(chain_factor_width + 1, reset=factor_reset)
        self.chain_a_offset = CSRStorage(width)
        self.chain_b_offset = CSRStorage(width)
        self.combined_offset = CSRStorage(width)
        self.combined_offset_signed = Signal((width, True))
        self.out_offset = CSRStorage(width)
        self.slow_decimation = CSRStorage(bits_for(16))
        for i in range(1, 4):
            setattr(self, f"analog_out_{i}", CSRStorage(15, name=f"analog_out_{i}"))

        self.slow_value = CSRStatus(width)

        self.chain_a_offset_signed = Signal((width, True))
        self.chain_b_offset_signed = Signal((width, True))
        self.out_offset_signed = Signal((width, True))

    def init_submodules(self, width, signal_width):
        self.submodules.mod = Modulate(width=width)
        self.submodules.sweep = SweepCSR(width=width, step_width=30, step_shift=24)
        self.submodules.limit_error_signal = LimitCSR(width=signal_width, guard=4)
        self.submodules.limit_fast1 = LimitCSR(width=width, guard=5)
        self.submodules.limit_fast2 = LimitCSR(width=width, guard=5)
        self.submodules.pid = PID(width=signal_width)
        self.submodules.autolock = FPGAAutolock(width=width, max_delay=8191)

    def connect_pid(self):
        # pid is not started directly by `request_lock` signal. Instead, `request_lock`
        # queues a run that is then started when the sweep is at the zero crossing
        self.comb += [
            self.pid.running.eq(self.autolock.lock_running.status),
            self.sweep.hold.eq(self.autolock.lock_running.status),
            self.autolock.fast.sweep_value.eq(self.sweep.y),
            self.autolock.fast.sweep_up.eq(self.sweep.sweep.up),
            self.autolock.fast.sweep_step.eq(
                self.sweep.step.storage >> self.sweep.step_shift
            ),
            self.autolock.robust.sweep_up.eq(self.sweep.sweep.up),
        ]

    def connect_everything(self, width, signal_width, coeff_width):
        combined_error_signal = Signal((signal_width, True))
        self.control_signal = Signal((signal_width, True))

        # additional IIR filter that prevents aliasing effects when recording PSD of
        # error signal
        self.submodules.raw_acquisition_iir = Iir(
            width=signal_width,
            coeff_width=coeff_width,
            shift=coeff_width - 2,
            order=5,
        )
        combined_error_signal_filtered = Signal((signal_width, True))
        self.comb += [
            self.raw_acquisition_iir.x.eq(combined_error_signal),
            self.raw_acquisition_iir.hold.eq(0),
            self.raw_acquisition_iir.clear.eq(0),
            combined_error_signal_filtered.eq(self.raw_acquisition_iir.y),
        ]

        self.sync += [
            self.chain_a_offset_signed.eq(self.chain_a_offset.storage),
            self.chain_b_offset_signed.eq(self.chain_b_offset.storage),
            self.combined_offset_signed.eq(self.combined_offset.storage),
            self.out_offset_signed.eq(self.out_offset.storage),
        ]

        self.state_in = []
        self.signal_in = []
        self.state_out = []
        self.signal_out = [
            self.control_signal,
            combined_error_signal,
            combined_error_signal_filtered,
        ]

        self.comb += [
            combined_error_signal.eq(self.limit_error_signal.y),
            self.control_signal.eq(
                Array([self.limit_fast1.y, self.limit_fast2.y])[
                    self.control_channel.storage
                ]
                << signal_width - width
            ),
        ]


class LinienModule(Module, AutoCSR):
    def __init__(self, platform):
        width = 14
        signal_width = 25
        coeff_width = 25
        chain_factor_bits = 8

        self.init_submodules(
            width, signal_width, coeff_width, chain_factor_bits, platform
        )
        self.connect_everything(width, signal_width, coeff_width, chain_factor_bits)

    def init_submodules(
        self, width, signal_width, coeff_width, chain_factor_bits, platform
    ):
        sys_double = ClockDomainsRenamer("sys_double")

        self.submodules.logic = LinienLogic(
            coeff_width=coeff_width, chain_factor_width=chain_factor_bits
        )
        self.submodules.analog = PitayaAnalog(
            platform.request("adc"), platform.request("dac")
        )
        self.submodules.xadc = XADC(platform.request("xadc"))

        for i in range(4):
            pwm = platform.request("pwm", i)
            ds = sys_double(DeltaSigma(width=15))
            self.comb += pwm.eq(ds.out)
            setattr(self.submodules, f"ds{i}", ds)

        exp = platform.request("exp")
        self.submodules.gpio_n = Gpio(exp.n)
        self.submodules.gpio_p = Gpio(exp.p)

        leds = Cat(*(platform.request("user_led", i) for i in range(8)))
        self.comb += leds.eq(self.gpio_n.o)

        self.submodules.dna = DNA(version=2)

        self.submodules.fast_a = FastChain(
            width,
            signal_width,
            coeff_width,
            self.logic.mod,
            offset_signal=self.logic.chain_a_offset_signed,
        )
        self.submodules.fast_b = FastChain(
            width,
            signal_width,
            coeff_width,
            self.logic.mod,
            offset_signal=self.logic.chain_b_offset_signed,
        )

        _ = ClockDomainsRenamer("sys_slow")
        sys_double = ClockDomainsRenamer("sys_double")
        max_decimation = 16
        self.submodules.decimate = sys_double(Decimate(max_decimation))
        self.clock_domains.cd_decimated_clock = ClockDomain()
        decimated_clock = ClockDomainsRenamer("decimated_clock")
        self.submodules.slow_chain = decimated_clock(SlowChain())

        self.submodules.scopegen = ScopeGen(signal_width)

        self.state_names, self.signal_names = cross_connect(
            self.gpio_n,
            [
                ("fast_a", self.fast_a),
                ("fast_b", self.fast_b),
                ("slow_chain", self.slow_chain),
                ("scopegen", self.scopegen),
                ("logic", self.logic),
                ("robust", self.logic.autolock.robust),
            ],
        )

        csr_map = {
            "dna": 28,
            "xadc": 29,
            "gpio_n": 30,
            "gpio_p": 31,
            "fast_a": 0,
            "fast_b": 1,
            "slow_chain": 2,
            "scopegen": 6,
            "noise": 7,
            "logic": 8,
        }

        self.submodules.csrbanks = csr_bus.CSRBankArray(
            self,
            lambda name, mem: csr_map[
                name if mem is None else name + "_" + mem.name_override
            ],
        )
        self.submodules.sys2csr = Sys2CSR()
        self.submodules.csrcon = csr_bus.Interconnect(
            self.sys2csr.csr, self.csrbanks.get_buses()
        )
        self.submodules.syscdc = SysCDC()
        self.comb += self.syscdc.target.connect(self.sys2csr.sys)

    def connect_everything(self, width, signal_width, coeff_width, chain_factor_bits):
        s = signal_width - width

        self.comb += [
            self.fast_a.adc.eq(self.analog.adc_a),
            self.fast_b.adc.eq(self.analog.adc_b),
        ]

        # now, we combine the output of the two paths, with a variable factor each.
        mixed = Signal(
            (2 + ((signal_width + 1) + self.logic.chain_a_factor.size), True)
        )
        self.comb += [
            If(
                self.logic.dual_channel.storage,
                mixed.eq(
                    (self.logic.chain_a_factor.storage * self.fast_a.out_i)
                    + (self.logic.chain_b_factor.storage * self.fast_b.out_i)
                    + (self.logic.combined_offset_signed << (chain_factor_bits + s))
                ),
            ).Else(
                mixed.eq(
                    (self.fast_a.out_i << chain_factor_bits)
                    + (self.logic.combined_offset_signed << (chain_factor_bits + s))
                )
            )
        ]

        mixed_limited = Signal((signal_width, True))
        self.comb += [
            self.logic.limit_error_signal.x.eq(mixed >> chain_factor_bits),
            mixed_limited.eq(self.logic.limit_error_signal.y),
        ]

        # FAST PID ---------------------------------------------------------------------
        pid_out = Signal((width, True))
        self.comb += [
            If(
                self.logic.pid_only_mode.storage,
                self.logic.pid.input.eq(self.analog.adc_a << s),
            ).Else(
                self.logic.pid.input.eq(mixed_limited),
            ),
            pid_out.eq(self.logic.pid.pid_out >> s),
        ]

        # SLOW PID ---------------------------------------------------------------------
        self.comb += [
            self.slow_chain.pid.running.eq(self.logic.autolock.lock_running.status),
            self.slow_chain.input.eq(self.logic.control_signal >> s),
            self.decimate.decimation.eq(self.logic.slow_decimation.storage),
            self.cd_decimated_clock.clk.eq(self.decimate.output),
            self.logic.slow_value.status.eq(self.slow_chain.output),
        ]

        # FAST OUTPUTS -----------------------------------------------------------------
        fast_outs = [Signal((width + 4, True)), Signal((width + 4, True))]
        for n_channel, fast_out in enumerate(fast_outs):
            self.comb += fast_out.eq(
                Mux(
                    self.logic.control_channel.storage == n_channel,
                    pid_out,
                    0,
                )
                + Mux(
                    self.logic.mod_channel.storage == n_channel,
                    self.logic.mod.y,
                    0,
                )
                + Mux(
                    self.logic.sweep_channel.storage == n_channel,
                    self.logic.sweep.y,
                    0,
                )
                + Mux(
                    self.logic.sweep_channel.storage == n_channel,
                    self.logic.out_offset_signed,
                    0,
                )
                + Mux(
                    self.logic.slow_control_channel.storage == n_channel,
                    self.slow_chain.output,
                    0,
                )
            )

        # ANALOG OUTPUTS ---------------------------------------------------------------
        # ANALOG OUT 0 gets a special treatment because it may contain signal of  slow
        # pid or sweep
        analog_out = Signal((width + 3, True))
        self.comb += [
            analog_out.eq(
                Mux(
                    self.logic.sweep_channel.storage == OutputChannel.ANALOG_OUT0,
                    self.logic.sweep.y,
                    0,
                )
                + Mux(
                    self.logic.sweep_channel.storage == OutputChannel.ANALOG_OUT0,
                    self.logic.out_offset_signed,
                    0,
                )
                + Mux(
                    self.logic.slow_control_channel.storage
                    == OutputChannel.ANALOG_OUT0,
                    self.slow_chain.output,
                    0,
                )
            ),
        ]
        # NOTE: not sure why limit is used
        self.comb += self.slow_chain.limit.x.eq(analog_out)
        # ds0 apparently has 16 bit, but only allowing positive  values --> "15 bit"?
        slow_out_shifted = Signal(15)
        self.sync += slow_out_shifted.eq((self.slow_chain.limit.y << 1) + (1 << 14))
        self.comb += self.ds0.data.eq(slow_out_shifted)

        # connect other analog outputs
        self.comb += [
            self.ds1.data.eq(self.logic.analog_out_1.storage),
            self.ds2.data.eq(self.logic.analog_out_2.storage),
            self.ds3.data.eq(self.logic.analog_out_3.storage),
        ]

        # ------------------------------------------------------------------------------

        self.sync += [
            self.logic.autolock.robust.input.eq(self.scopegen.scope_written_data),
            # `writing_data_now` is intentionally delayed by one cycle here in order to
            # prevent glitches
            self.logic.autolock.robust.writing_data_now.eq(
                self.scopegen.writing_data_now
            ),
        ]

        self.comb += [
            self.logic.autolock.robust.at_start.eq(self.logic.sweep.sweep.trigger),
            self.scopegen.gpio_trigger.eq(self.gpio_p.i[0]),
            self.scopegen.sweep_trigger.eq(self.logic.sweep.sweep.trigger),
            self.scopegen.automatically_rearm.eq(
                self.logic.autolock.request_lock.storage
                & ~self.logic.autolock.lock_running.status
            ),
            self.scopegen.automatically_trigger.eq(
                self.logic.autolock.lock_running.status
            ),
            self.analog.dac_a.eq(self.logic.limit_fast1.y),
            self.analog.dac_b.eq(self.logic.limit_fast2.y),
        ]

        # Having this in a comb statement caused errors. See PR #251.
        self.sync += [
            self.logic.limit_fast1.x.eq(fast_outs[0]),
            self.logic.limit_fast2.x.eq(fast_outs[1]),
        ]


class DummyID(Module, AutoCSR):
    def __init__(self):
        self.id = CSRStatus(1, reset=1)


class DummyHK(Module, AutoCSR):
    def __init__(self):
        self.submodules.id = DummyID()
        self.submodules.csrbanks = csr_bus.CSRBankArray(self, lambda name, mem: 0)
        self.submodules.sys2csr = Sys2CSR()
        self.submodules.csrcon = csr_bus.Interconnect(
            self.sys2csr.csr, self.csrbanks.get_buses()
        )
        self.sys = self.sys2csr.sys


class RootModule(Module):
    def __init__(self, platform):
        self.submodules.ps = PitayaPS(platform.request("cpu"))
        self.submodules.crg = CRG(
            platform.request("clk125"), self.ps.fclk[0], ~self.ps.frstn[0]
        )
        self.submodules.linien = LinienModule(platform)

        self.submodules.hk = ClockDomainsRenamer("sys_ps")(DummyHK())

        self.submodules.ic = SysInterconnect(
            self.ps.axi.sys,
            self.hk.sys,
            self.linien.scopegen.scope_sys,
            self.linien.scopegen.asg_sys,
            self.linien.syscdc.source,
        )
