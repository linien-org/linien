from linien.common import AUTOLOCK_MAX_N_INSTRUCTIONS
from migen import (
    Array,
    If,
    Module,
    Signal,
    bits_for,
    run_simulation,
    ClockDomainsRenamer,
    ClockDomain,
)
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage


class DynamicDelay(Module):
    """Delays a signal `self.input` of length `input_bit` by a dynamic number
    of clock cycles (`max_delay` is the maximum number of clock cycles).
    `self.output` contains the delayed signal.

    Internally, this module uses an array of registers. Set `restart` to 1 if you
    want to delete everything stored in these registers.
    """

    def __init__(self, input_bit, max_delay):
        self.delay = Signal(bits_for(max_delay))
        self.restart = Signal()
        self.writing_data_now = Signal()

        self.input = Signal((input_bit, True))
        self.output = Signal((input_bit, True))

        registers = [Signal((input_bit, True)) for _ in range(max_delay)]

        self.comb += [registers[0].eq(self.input)]

        for idx, register in enumerate(registers):
            if idx < len(registers) - 1:
                next_register = registers[idx + 1]
                self.sync += [
                    If(self.restart, next_register.eq(0)).Else(
                        If(self.writing_data_now, next_register.eq(register)),
                    )
                ]

        self.comb += [self.output.eq(Array(registers)[self.delay])]


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


class FPGAAutolock(Module, AutoCSR):
    def __init__(self, width=14, N_points=16383, max_delay=16383):
        self.submodules.robust = RobustAutolock(max_delay=max_delay)

        self.submodules.fast = FastAutolock(width=width)

        self.request_lock = CSRStorage()
        self.autolock_mode = CSRStorage()
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
                & (self.autolock_mode.storage == 0),
                self.lock_running.status.eq(1),
            ),
            If(
                self.request_lock.storage
                & self.robust.turn_on_lock
                & (self.autolock_mode.storage == 1),
                self.lock_running.status.eq(1),
            ),
        ]


class FastAutolock(Module, AutoCSR):
    def __init__(self, width=14):
        # pid is not started directly by `request_lock` signal. Instead, `request_lock`
        # queues a run that is then started when the ramp is at the zero target position
        self.request_lock = Signal()
        self.turn_on_lock = Signal()
        self.sweep_value = Signal((width, True))
        self.sweep_step = Signal(width)
        self.sweep_up = Signal()

        self.target_position = CSRStorage(width)
        target_position_signed = Signal((width, True))

        self.comb += [target_position_signed.eq(self.target_position.storage)]

        self.sync += [
            If(~self.request_lock, self.turn_on_lock.eq(0),).Else(
                self.turn_on_lock.eq(
                    (
                        self.sweep_value
                        >= target_position_signed - (self.sweep_step >> 1)
                    )
                    & (
                        self.sweep_value
                        <= target_position_signed + 1 + (self.sweep_step >> 1)
                    )
                    # and if the ramp is going up (because this is when a
                    # spectrum is recorded)
                    & (self.sweep_up)
                ),
            ),
        ]


class RobustAutolock(Module, AutoCSR):
    def __init__(self, width=14, N_points=16383, max_delay=16383):
        self.at_start = Signal()
        self.writing_data_now = Signal()
        self.sweep_up = Signal()

        # FIXME: Remove this?
        # FIXME: cleanup all these test signals
        signal_width = 25
        test_sum = Signal((signal_width, True))
        test_sum_diff = Signal((signal_width, True))

        state_always_on = Signal()
        watching = Signal()

        self.request_lock = Signal()

        self.input = Signal((width, True))
        self.time_scale = CSRStorage(bits_for(N_points))

        self.submodules.sum_diff_calculator = SumDiffCalculator(
            width, N_points, max_delay=max_delay
        )

        self.current_instruction_idx = Signal(bits_for(AUTOLOCK_MAX_N_INSTRUCTIONS - 1))
        self.N_instructions = CSRStorage(bits_for(AUTOLOCK_MAX_N_INSTRUCTIONS - 1))
        self.turn_on_lock = Signal()

        peak_height_bit = len(self.sum_diff_calculator.sum_value)
        self.peak_heights = [
            CSRStorage(peak_height_bit, name="peak_height_%d" % idx)
            for idx in range(AUTOLOCK_MAX_N_INSTRUCTIONS)
        ]
        for idx, peak_height in enumerate(self.peak_heights):
            setattr(self, "peak_height_%d" % idx, peak_height)

        x_data_length_bit = bits_for(N_points)
        self.wait_for = [
            CSRStorage(x_data_length_bit, name="wait_for_%d" % idx)
            for idx in range(AUTOLOCK_MAX_N_INSTRUCTIONS)
        ]
        for idx, wait_for in enumerate(self.wait_for):
            setattr(self, "wait_for_%d" % idx, wait_for)

        current_peak_height = Signal((peak_height_bit, True))
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

        waited_for = Signal(bits_for(N_points))
        waited_for_shifted = Signal(25)
        current_peak_height_shifted = Signal(25)
        current_wait_for_shifted = Signal(25)
        input_shifted = Signal((25, True))

        self.comb += [
            test_sum.eq(
                self.sum_diff_calculator.sum_value
                >> (len(self.sum_diff_calculator.sum_value) - signal_width)
            ),
            test_sum_diff.eq(
                self.sum_diff_calculator.output
                >> (len(self.sum_diff_calculator.output) - signal_width)
            ),
            state_always_on.eq(1),
            waited_for_shifted.eq(waited_for << 11),
            current_peak_height_shifted.eq(
                current_peak_height
                >> (len(self.sum_diff_calculator.sum_value) - signal_width)
            ),
            current_wait_for_shifted.eq(current_wait_for << 11),
            input_shifted.eq(self.input << 11),
        ]

        sum_diff = Signal((len(self.sum_diff_calculator.output), True))
        sign_equal = Signal()
        over_threshold = Signal()
        waited_long_enough = Signal()
        instruction_idx_at_zero = Signal()
        self.comb += [instruction_idx_at_zero.eq(self.current_instruction_idx == 0)]

        self.signal_out = [
            test_sum,
            test_sum_diff,
            waited_for_shifted,
            current_peak_height_shifted,
            current_wait_for_shifted,
            input_shifted,
        ]
        self.signal_in = []
        self.state_out = [
            state_always_on,
            watching,
            self.turn_on_lock,
            sign_equal,
            over_threshold,
            waited_long_enough,
            instruction_idx_at_zero,
        ]
        self.state_in = []

        abs_sum_diff = Signal.like(sum_diff)
        abs_current_peak_height = Signal.like(current_peak_height)

        self.comb += [
            self.sum_diff_calculator.writing_data_now.eq(self.writing_data_now),
            self.sum_diff_calculator.restart.eq(self.at_start),
            self.sum_diff_calculator.input.eq(self.input),
            self.sum_diff_calculator.delay_value.eq(self.time_scale.storage),
            sum_diff.eq(self.sum_diff_calculator.output),
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
            self.turn_on_lock.eq(
                self.current_instruction_idx >= self.N_instructions.storage
            ),
        ]

        self.sign_equal_csr = CSRStatus()
        self.current_instruction_idx_csr = CSRStatus()
        self.current_peak_height_csr = CSRStatus(peak_height_bit)
        self.comb += [
            self.sign_equal_csr.status.eq(sign_equal),
            self.current_instruction_idx_csr.status.eq(self.current_instruction_idx),
            self.current_peak_height_csr.status.eq(current_peak_height),
        ]

        self.sync += [
            If(
                self.at_start,
                waited_for.eq(0),
                self.current_instruction_idx.eq(0),
                If(self.request_lock, watching.eq(1)).Else(watching.eq(0)),
            ).Else(
                # not at start
                If(
                    ~self.request_lock,
                    # disable `watching` if `request_lock` was disabled while
                    # the ramp is running. This is important for slow scan
                    # speeds when disabling the autolock and enabling it again
                    # with different parameters. In this case we want to take
                    # care that we start watching at start.
                    watching.eq(0),
                ),
                If(
                    self.writing_data_now & ~self.turn_on_lock & self.sweep_up,
                    If(
                        watching & sign_equal & over_threshold & waited_long_enough,
                        self.current_instruction_idx.eq(
                            self.current_instruction_idx + 1
                        ),
                        waited_for.eq(0),
                    ).Else(waited_for.eq(waited_for + 1)),
                ),
            ),
        ]


def get_lock_position_from_autolock_instructions_by_simulating_fpga(
    spectrum, description, time_scale, initial_spectrum
):
    result = {}

    def tb(dut):
        yield dut.sweep_up.eq(1)
        yield dut.request_lock.eq(1)
        yield dut.at_start.eq(1)
        yield dut.writing_data_now.eq(1)

        yield dut.N_instructions.storage.eq(len(description))

        for description_idx, [wait_for, current_threshold] in enumerate(description):
            yield dut.peak_heights[description_idx].storage.eq(int(current_threshold))
            yield dut.wait_for[description_idx].storage.eq(int(wait_for))

        yield

        yield dut.at_start.eq(0)
        yield dut.time_scale.storage.eq(int(time_scale))

        for i in range(len(spectrum)):
            yield dut.input.eq(int(spectrum[i]))

            turn_on_lock = yield dut.turn_on_lock
            if turn_on_lock:
                result["index"] = i
                return

            yield

    dut = RobustAutolock(max_delay=time_scale + 5)
    run_simulation(
        dut, tb(dut), vcd_name="experimental_autolock_fpga_lock_position_finder.vcd"
    )

    return result.get("index")
