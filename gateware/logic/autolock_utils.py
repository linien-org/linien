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

from migen import If, Module, Signal, bits_for
from misoc.interconnect.csr import Memory


def create_memory(self, N_bits, N_points, name):
    setattr(self.specials, name, Memory(N_bits, N_points, name=name))
    mem = getattr(self, name)

    rdport = mem.get_port()
    wrport = mem.get_port(write_capable=True)

    return rdport, wrport


class DynamicDelay(Module):
    """Delays a signal `self.input` of length `input_bit` by a dynamic number
    of clock cycles (`max_delay` is the maximum number of clock cycles).
    `self.output` contains the delayed signal.

    Internally, this module uses a memory. Set `restart` to 1 if you
    want to delete everything stored in this memory.
    """

    def __init__(self, input_bit, max_delay):
        self.delay = Signal(bits_for(max_delay))
        self.restart = Signal()
        self.writing_data_now = Signal()

        self.input = Signal((input_bit, True))
        self.output = Signal((input_bit, True))

        # this ensures that counter overflows / underflows correctly
        assert max_delay == (2 ** (bits_for(max_delay)) - 1)

        self.mem_rdport, self.mem_wrport = create_memory(
            self, input_bit, max_delay, "dynamic_delay_mem"
        )

        # register all the ports
        self.specials += [self.mem_rdport, self.mem_wrport]

        self.counter = Signal(bits_for(max_delay))
        self.counter_delayed = Signal((bits_for(max_delay)))

        negative_delay = 1

        self.sync += [
            If(self.restart, self.counter.eq(0)).Else(
                If(self.writing_data_now, self.counter.eq(self.counter + 1))
            ),
        ]
        self.comb += [
            self.mem_wrport.we.eq(self.writing_data_now),
            self.mem_wrport.adr.eq(self.counter),
            self.mem_wrport.dat_w.eq(self.input),
            self.mem_rdport.adr.eq(self.counter_delayed),
            self.counter_delayed.eq(self.counter - self.delay + negative_delay),
            self.mem_rdport.adr.eq(self.counter_delayed),
            If(self.counter < self.delay - negative_delay, self.output.eq(0)).Else(
                self.output.eq(self.mem_rdport.dat_r),
            ),
        ]


class SumDiffCalculator(Module):
    """The autolock requires the integral of the spectrum over the last few values
    in a moving window. This module provides this quantity by summing over all
    values of the spectrum and comparing the current value of this sum with a
    delayed version.

    `width` is the signal width and `N_points` is the length of the spectrum.
    `self.input` is the input signal and `self.delay_value` the time constant
    in clock cycles. The result is stored in `self.output`.
    Use `self.restart` to restart the calculation.
    """

    def __init__(self, width=14, N_points=16383, max_delay=16383):
        self.restart = Signal()
        self.writing_data_now = Signal()

        self.input = Signal((width, True))
        self.delay_value = Signal(bits_for(N_points))

        sum_value_bits = bits_for(((2 ** width) - 1) * N_points)
        self.sum_value = Signal((sum_value_bits, True))
        delayed_sum = Signal((sum_value_bits, True))
        current_sum_diff = Signal((sum_value_bits + 1, True))
        self.output = Signal.like(current_sum_diff)

        self.submodules.delayer = DynamicDelay(sum_value_bits, max_delay=max_delay)

        self.sync += [
            If(self.restart, self.sum_value.eq(0),).Else(
                If(
                    self.writing_data_now,
                    # not at start
                    self.sum_value.eq(self.sum_value + self.input),
                )
            )
        ]

        self.comb += [
            self.delayer.writing_data_now.eq(self.writing_data_now),
            self.delayer.restart.eq(self.restart),
            self.delayer.delay.eq(self.delay_value),
            self.delayer.input.eq(self.sum_value),
            delayed_sum.eq(self.delayer.output),
            current_sum_diff.eq(self.sum_value - delayed_sum),
            self.output.eq(current_sum_diff),
        ]
