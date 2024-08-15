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

from migen import Array, ClockSignal, If, Instance, Module, Record, ResetSignal, Signal
from misoc.interconnect.csr import AutoCSR, CSRStorage

from .pitaya_ps import sys_layout


class ScopeGen(Module, AutoCSR):
    def __init__(self, width=25):
        self.gpio_trigger = Signal()
        self.sweep_trigger = Signal()

        # when lock is disabled and sweep enabled, acquisition process arms the
        # scope, waits until scope has triggered and reads out the data. Once
        # data is read out, it rearms the acquisition. When robust autolock is
        # looking for a lock point, acquisition process doesn't send any triggers
        # though because it doesn't transmit any data until lock is confirmed.
        # Therefore, autolock turns on "always_arm" mode which automatically
        # rearms scope when it has finished.
        self.automatically_rearm = Signal()

        # this mode is used when the laser is locked. In this case we don't have
        # to sync acquisition with a sweep. Synchronisation with readout takes
        # place by manually rearming after reading out the data.
        self.automatically_trigger = Signal()
        automatic_trigger_signal = Signal()
        self.sync += [
            If(
                self.automatically_trigger,
                automatic_trigger_signal.eq(~automatic_trigger_signal),
            ).Else(automatic_trigger_signal.eq(0))
        ]

        self.external_trigger = CSRStorage(1)
        ext_scope_trigger = Array([self.gpio_trigger, self.sweep_trigger])[
            self.external_trigger.storage
        ]

        self.scope_sys = Record(sys_layout)
        self.asg_sys = Record(sys_layout)

        adc_a = Signal((width, True))
        adc_a_q = Signal((width, True))
        adc_b = Signal((width, True))
        adc_b_q = Signal((width, True))
        dac_a = Signal((width, True))
        dac_b = Signal((width, True))

        self.signal_in = adc_a, adc_b, adc_a_q, adc_b_q
        self.signal_out = dac_a, dac_b
        self.state_in = ()
        self.state_out = ()

        asg_a = Signal((14, True))
        asg_b = Signal((14, True))
        asg_trig = Signal()

        s = width - len(asg_a)
        self.comb += dac_a.eq(asg_a << s), dac_b.eq(asg_b << s)

        # these signals will be connected to autolock which inspects written data
        self.writing_data_now = Signal()
        self.scope_written_data = Signal((14, True))
        self.scope_position = Signal(14)

        self.specials.scope = Instance(
            "red_pitaya_scope",
            i_automatically_rearm_i=self.automatically_rearm,
            i_adc_a_i=adc_a >> s,
            i_adc_b_i=adc_b >> s,
            i_adc_a_q_i=adc_a_q >> s,
            i_adc_b_q_i=adc_b_q >> s,
            # i_adc_a_q_i=0b11111111111111,
            # i_adc_b_q_i=0b11111111111111,
            i_adc_clk_i=ClockSignal(),
            i_adc_rstn_i=~ResetSignal(),
            i_trig_ext_i=ext_scope_trigger | automatic_trigger_signal,
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
            o_written_data=self.scope_written_data,
            o_scope_position=self.scope_position,
            o_scope_writing_now=self.writing_data_now,
        )
