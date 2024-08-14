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

from linien_common.common import AUTOLOCK_MAX_N_INSTRUCTIONS, AutolockMode
from migen import Array, If, Module, Signal, bits_for
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage

from .autolock_utils import SumDiffCalculator

ROBUST_AUTOLOCK_FPGA_DELAY = 3


class FPGAAutolock(Module, AutoCSR):
    """
    This class handles autolock on FPGA. It is the counterpart to the `Autolock` class
    in the server directory.

    Depending on `autolock_mode`, either fast or robust autolock is used. Independent of
    the mode selected, locking happens by setting `request_lock`. Once lock has been
    established, `lock_running` will be HIGH.
    """

    def __init__(self, width=14, N_points=16383, max_delay=16383):
        self.submodules.robust = RobustAutolock(max_delay=max_delay)

        self.submodules.fast = SimpleAutolock(width=width)

        self.request_lock = CSRStorage()
        self.autolock_mode = CSRStorage(2)
        self.lock_running = CSRStatus()

        self.comb += [
            self.fast.request_lock.eq(self.request_lock.storage),
            self.robust.request_lock.eq(self.request_lock.storage),
        ]

        self.sync += [
            If(
                ~self.request_lock.storage,
                self.lock_running.status.eq(0),
            ),
            If(
                self.request_lock.storage
                & self.fast.turn_on_lock
                & (self.autolock_mode.storage == AutolockMode.SIMPLE),
                self.lock_running.status.eq(1),
            ),
            If(
                self.request_lock.storage
                & self.robust.turn_on_lock
                & (self.autolock_mode.storage == AutolockMode.ROBUST),
                self.lock_running.status.eq(1),
            ),
        ]


class SimpleAutolock(Module, AutoCSR):
    """
    The operation of fast autolock is simple: wait until the sweep has reached a certain
    point and turn on the lock. This method is well suited for systems with not too much
    jitter.
    """

    def __init__(self, width=14):
        # pid is not started directly by `request_lock` signal. Instead, `request_lock`
        # queues a run that is then started when the sweep is at the zero target
        # position.
        self.request_lock = Signal()
        self.turn_on_lock = Signal()
        self.sweep_value = Signal((width, True))
        self.sweep_step = Signal(width)
        self.sweep_up = Signal()

        self.target_position = CSRStorage(width)
        target_position_signed = Signal((width, True))

        self.comb += [target_position_signed.eq(self.target_position.storage)]

        self.sync += [
            If(
                ~self.request_lock,
                self.turn_on_lock.eq(0),
            ).Else(
                self.turn_on_lock.eq(
                    (
                        self.sweep_value
                        >= target_position_signed - (self.sweep_step >> 1)
                    )
                    & (
                        self.sweep_value
                        <= target_position_signed + 1 + (self.sweep_step >> 1)
                    )
                    # and if the sweep is going up (because this is when a
                    # spectrum is recorded)
                    & (self.sweep_up)
                ),
            ),
        ]


class RobustAutolock(Module, AutoCSR):
    def __init__(self, width=14, N_points=16383, max_delay=16383):
        self.init_submodules(width, N_points, max_delay)
        peak_height_bit, x_data_length_bit = self.init_csr(N_points)
        self.init_inout_signals(width)

        # is the autolock actively trying to detect peaks? This is set to true
        # if lock is requested and once the sweep is at start
        watching = Signal()

        # the following signals are property of the peak that the autolock is trying to
        # detect right now
        self.current_instruction_idx = Signal(bits_for(AUTOLOCK_MAX_N_INSTRUCTIONS - 1))
        current_peak_height = Signal((peak_height_bit, True))
        abs_current_peak_height = Signal.like(current_peak_height)
        current_wait_for = Signal(x_data_length_bit)
        self.comb += [
            current_peak_height.eq(
                Array([peak_height.storage for peak_height in self.peak_heights])[
                    self.current_instruction_idx
                ]
            ),
            current_wait_for.eq(
                Array([wait_for.storage for wait_for in self.wait_for])[
                    self.current_instruction_idx
                ]
            ),
        ]

        # after detecting the last peak, how many cycles have passed?
        waited_for = Signal(bits_for(N_points))
        # after all peaks have been detected, how many cycles have passed?
        final_waited_for = Signal(bits_for(N_points))

        # this is the signal that's used for detecting peaks
        sum_diff = Signal((len(self.sum_diff_calculator.output), True))
        abs_sum_diff = Signal.like(sum_diff)
        self.comb += [
            self.sum_diff_calculator.writing_data_now.eq(self.writing_data_now),
            self.sum_diff_calculator.restart.eq(self.at_start),
            self.sum_diff_calculator.input.eq(self.input),
            self.sum_diff_calculator.delay_value.eq(self.time_scale.storage),
            sum_diff.eq(self.sum_diff_calculator.output),
        ]

        # has this signal at the moment the same sign as the peak we are looking for?
        sign_equal = Signal()
        # is this signal higher than the peak we are looking for?
        over_threshold = Signal()
        # since detecting the previous peak, has enough time passed?
        waited_long_enough = Signal()
        # have we detected all peaks (and can turn on the lock)?
        all_instructions_triggered = Signal()

        self.comb += [
            sign_equal.eq((sum_diff > 0) == (current_peak_height > 0)),
            If(sum_diff >= 0, abs_sum_diff.eq(sum_diff)).Else(
                abs_sum_diff.eq(-1 * sum_diff)
            ),
            If(
                current_peak_height >= 0,
                abs_current_peak_height.eq(current_peak_height),
            ).Else(abs_current_peak_height.eq(-1 * current_peak_height)),
            over_threshold.eq(abs_sum_diff >= abs_current_peak_height),
            waited_long_enough.eq(waited_for > current_wait_for),
            all_instructions_triggered.eq(
                self.current_instruction_idx >= self.N_instructions.storage
            ),
            self.turn_on_lock.eq(
                all_instructions_triggered
                & (final_waited_for >= self.final_wait_time.storage)
            ),
        ]

        self.sync += [
            If(
                self.at_start,
                waited_for.eq(0),
                # fpga robust autolock algorithm registeres trigger events delayed.
                # Therefore, we give it a head start for `final_waited_for`
                final_waited_for.eq(ROBUST_AUTOLOCK_FPGA_DELAY),
                self.current_instruction_idx.eq(0),
                If(self.request_lock, watching.eq(1)).Else(watching.eq(0)),
            ).Else(
                # not at start
                If(
                    ~self.request_lock,
                    # disable `watching` if `request_lock` was disabled while  the sweep
                    # is running. This is important for slow scan speeds when disabling
                    # the autolock and enabling it again with different parameters. In
                    # this case we want to take care that we start watching at start.
                    watching.eq(0),
                ),
                If(
                    self.writing_data_now & ~all_instructions_triggered & self.sweep_up,
                    If(
                        watching & sign_equal & over_threshold & waited_long_enough,
                        self.current_instruction_idx.eq(
                            self.current_instruction_idx + 1
                        ),
                        waited_for.eq(0),
                    ).Else(waited_for.eq(waited_for + 1)),
                ),
                If(
                    self.writing_data_now & all_instructions_triggered & self.sweep_up,
                    final_waited_for.eq(final_waited_for + 1),
                ),
            ),
        ]

        self.signal_out = []
        self.signal_in = []
        self.state_out = [
            watching,
            self.turn_on_lock,
            sign_equal,
            over_threshold,
            waited_long_enough,
        ]
        self.state_in = []

    def init_submodules(self, width, N_points, max_delay):
        self.submodules.sum_diff_calculator = SumDiffCalculator(
            width, N_points, max_delay=max_delay
        )

    def init_csr(self, N_points):
        # CSR storages
        self.time_scale = CSRStorage(bits_for(N_points))
        self.N_instructions = CSRStorage(bits_for(AUTOLOCK_MAX_N_INSTRUCTIONS - 1))
        self.final_wait_time = CSRStorage(bits_for(N_points))

        peak_height_bit = len(self.sum_diff_calculator.sum_value)
        self.peak_heights = [
            CSRStorage(peak_height_bit, name=f"peak_height_{idx}")
            for idx in range(AUTOLOCK_MAX_N_INSTRUCTIONS)
        ]
        for idx, peak_height in enumerate(self.peak_heights):
            setattr(self, f"peak_height_{idx}", peak_height)

        x_data_length_bit = bits_for(N_points)
        self.wait_for = [
            CSRStorage(x_data_length_bit, name=f"wait_for_{idx}")
            for idx in range(AUTOLOCK_MAX_N_INSTRUCTIONS)
        ]
        for idx, wait_for in enumerate(self.wait_for):
            setattr(self, f"wait_for_{idx}", wait_for)

        return peak_height_bit, x_data_length_bit

    def init_inout_signals(self, width):
        # signals that are connected to other modules
        self.input = Signal((width, True))
        self.request_lock = Signal()
        self.at_start = Signal()
        self.writing_data_now = Signal()
        self.sweep_up = Signal()
        self.turn_on_lock = Signal()
