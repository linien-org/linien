# this code is based on redpid. See LICENSE for details.
from migen import (
    Signal,
    Module,
    bits_for,
    Array,
    ClockDomainsRenamer,
    Cat,
    ClockDomain,
    If,
    Mux,
)
from misoc.interconnect import csr_bus
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage

from linien.common import ANALOG_OUT0

from .logic.chains import FastChain, SlowChain, cross_connect
from .logic.decimation import Decimate
from .logic.delta_sigma import DeltaSigma
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
    def __init__(self, width=14, signal_width=25, chain_factor_width=8):
        self.init_csr(width, signal_width, chain_factor_width)
        self.init_submodules(width, signal_width)
        self.connect_pid()
        self.connect_everything(width, signal_width)

    def init_csr(self, width, signal_width, chain_factor_width):
        factor_reset = 1 << (chain_factor_width - 1)
        # we use chain_factor_width + 1 for the single channel mode
        self.dual_channel = CSRStorage(1)
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

        self.slow_value = CSRStatus(width)

        max_decimation = 16
        self.slow_decimation = CSRStorage(bits_for(max_decimation))

        for i in range(4):
            if i == 0:
                continue
            name = 'analog_out_%d' % i
            setattr(self, name, CSRStorage(15, name=name))

    def init_submodules(self, width, signal_width):
        self.submodules.mod = Modulate(width=width)
        self.submodules.sweep = SweepCSR(width=width, step_width=30, step_shift=24)
        self.submodules.limit_error_signal = LimitCSR(width=signal_width, guard=4)
        self.submodules.limit_fast1 = LimitCSR(width=width, guard=5)
        self.submodules.limit_fast2 = LimitCSR(width=width, guard=5)
        self.submodules.pid = PID(width=signal_width)

    def connect_pid(self):
        # pid is not started directly by `request_lock` signal. Instead, `request_lock`
        # queues a run that is then started when the ramp is at the zero crossing
        self.request_lock = CSRStorage()
        self.lock_running = CSRStatus()
        ready_for_lock = Signal()

        self.comb += [
            self.pid.running.eq(self.lock_running.status),
            self.sweep.clear.eq(self.lock_running.status),
            self.sweep.hold.eq(0),
        ]

        self.sync += [
            If(~self.request_lock.storage,
                self.lock_running.status.eq(0),
                ready_for_lock.eq(0)
            ),

            If(self.request_lock.storage & ~ready_for_lock,
                ready_for_lock.eq(
                    # set ready for lock if sweep is at zero crossing
                    (self.sweep.sweep.y > 0)
                    & (self.sweep.sweep.y <= self.sweep.sweep.step)
                    # and if the ramp is going up (because this is when a
                    # spectrum is recorded)
                    & (self.sweep.sweep.up)
                )
            ),
            If(self.request_lock.storage & ready_for_lock,
                self.lock_running.status.eq(1)
            ),
        ]

    def connect_everything(self, width, signal_width):
        s = signal_width - width

        combined_error_signal = Signal((signal_width, True))
        self.control_signal = Signal((signal_width, True))

        self.sync += [
            self.chain_a_offset_signed.eq(self.chain_a_offset.storage),
            self.chain_b_offset_signed.eq(self.chain_b_offset.storage),
            self.combined_offset_signed.eq(self.combined_offset.storage),
            self.out_offset_signed.eq(self.out_offset.storage),
        ]

        self.state_in = []
        self.signal_in = []
        self.state_out = []
        self.signal_out = [self.control_signal, combined_error_signal]


        self.comb += [
            combined_error_signal.eq(self.limit_error_signal.y),
            self.control_signal.eq(
                Array([self.limit_fast1.y, self.limit_fast2.y])[
                    self.control_channel.storage
                ]
                << s
            ),
        ]


class LinienModule(Module, AutoCSR):
    def __init__(self, platform):
        width = 14
        signal_width, coeff_width = 25, 25
        chain_factor_bits = 8

        self.init_submodules(width, signal_width, coeff_width, chain_factor_bits, platform)
        self.connect_everything(width, signal_width, coeff_width, chain_factor_bits)

    def init_submodules(self, width, signal_width, coeff_width, chain_factor_bits, platform):
        sys_double = ClockDomainsRenamer("sys_double")

        self.submodules.logic = LinienLogic(chain_factor_width=chain_factor_bits)
        self.submodules.analog = PitayaAnalog(
            platform.request("adc"), platform.request("dac")
        )
        self.submodules.xadc = XADC(platform.request("xadc"))

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

        sys_slow = ClockDomainsRenamer("sys_slow")
        sys_double = ClockDomainsRenamer("sys_double")
        max_decimation = 16
        self.submodules.decimate = sys_double(Decimate(max_decimation))
        self.clock_domains.cd_decimated_clock = ClockDomain()
        decimated_clock = ClockDomainsRenamer("decimated_clock")
        self.submodules.slow = decimated_clock(SlowChain())

        self.submodules.scopegen = ScopeGen(signal_width)

        self.state_names, self.signal_names = cross_connect(
            self.gpio_n,
            [
                ("fast_a", self.fast_a),
                ("fast_b", self.fast_b),
                ("slow", self.slow),
                ("scopegen", self.scopegen),
                ("logic", self.logic),
            ],
        )

        csr_map = {
            "dna": 28,
            "xadc": 29,
            "gpio_n": 30,
            "gpio_p": 31,
            "fast_a": 0,
            "fast_b": 1,
            "slow": 2,
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
            self.fast_b.adc.eq(self.analog.adc_b)
        ]

        # now, we combine the output of the two paths, with a variable
        # factor each.
        mixed = Signal((2 + ((signal_width + 1) + self.logic.chain_a_factor.size), True))
        self.comb += [
            If(
                self.logic.dual_channel.storage,
                mixed.eq(
                    (self.logic.chain_a_factor.storage * self.fast_a.out_i)
                    + (self.logic.chain_b_factor.storage * self.fast_b.out_i)
                    + (self.logic.combined_offset_signed << (chain_factor_bits + s))
                ),
            ).Else(mixed.eq(self.fast_a.out_i << chain_factor_bits))
        ]

        mixed_limited = Signal((signal_width, True))
        self.comb += [
            self.logic.limit_error_signal.x.eq(mixed >> chain_factor_bits),
            mixed_limited.eq(self.logic.limit_error_signal.y),
        ]

        pid_out = Signal((width, True))
        self.comb += [
            self.logic.pid.input.eq(mixed_limited),
            pid_out.eq(self.logic.pid.pid_out >> s),
        ]

        fast_outs = list(Signal((width + 4, True)) for channel in (0, 1))

        for channel, fast_out in enumerate(fast_outs):
            self.comb += fast_out.eq(
                Mux(self.logic.control_channel.storage == channel, pid_out, 0)
                + Mux(self.logic.mod_channel.storage == channel, self.logic.mod.y, 0)
                + Mux(self.logic.sweep_channel.storage == channel, self.logic.sweep.y, 0)
                + Mux(
                    self.logic.sweep_channel.storage == channel,
                    self.logic.out_offset_signed,
                    0,
                )
            )

        for analog_idx in range(4):
            if analog_idx == 0:
                # first analog out gets a special treatment bc it may
                # contain signal of slow pid or sweep

                self.comb += self.slow.pid.running.eq(self.logic.lock_running.status)

                slow_pid_out = Signal((width, True))
                self.comb += slow_pid_out.eq(self.slow.output)

                slow_out = Signal((width + 3, True))
                self.comb += [
                    slow_out.eq(
                        slow_pid_out
                        + Mux(
                            self.logic.sweep_channel.storage == ANALOG_OUT0,
                            self.logic.sweep.y,
                            0
                        )
                        + Mux(
                            self.logic.sweep_channel.storage == ANALOG_OUT0,
                            self.logic.out_offset_signed,
                            0,
                        )
                    ),
                    self.slow.limit.x.eq(slow_out),
                ]

                slow_out_shifted = Signal(15)
                self.sync += slow_out_shifted.eq(
                    # ds0 apparently has 16 bit, but only allowing positive
                    # values --> "15 bit"?
                    (self.slow.limit.y << 1)
                    + (1 << 14)
                )

                analog_out = slow_out_shifted
            else:
                # 15 bit
                dc_source = [
                    None,
                    self.logic.analog_out_1.storage,
                    self.logic.analog_out_2.storage,
                    self.logic.analog_out_3.storage,
                ][analog_idx]
                analog_out = dc_source

            dss = [self.ds0, self.ds1, self.ds2, self.ds3]
            self.comb += dss[analog_idx].data.eq(analog_out)

        self.comb += [
            self.scopegen.gpio_trigger.eq(self.gpio_p.i[0]),
            self.scopegen.sweep_trigger.eq(self.logic.sweep.sweep.trigger),
            self.logic.limit_fast1.x.eq(fast_outs[0]),
            self.logic.limit_fast2.x.eq(fast_outs[1]),
            self.analog.dac_a.eq(self.logic.limit_fast1.y),
            self.analog.dac_b.eq(self.logic.limit_fast2.y),

            # SLOW OUT
            self.slow.input.eq(self.logic.control_signal >> s),
            self.decimate.decimation.eq(self.logic.slow_decimation.storage),
            self.cd_decimated_clock.clk.eq(self.decimate.output),
            self.logic.slow_value.status.eq(self.slow.limit.y),
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

