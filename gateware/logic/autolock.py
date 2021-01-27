from migen import Array, If, Module, Signal, bits_for, run_simulation
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage


class DynamicDelay(Module):
    """Delays a signal `self.input` of length `input_bit` by a dynamic number
    of clock cycles (`max_delay` is the maximum number of clock cycles).
    `self.output` contains the delayed signal.

    Internally, this module uses an array of registers. Set `reset` to 1 if you
    want to delete everything stored in these registers.
    """
    def __init__(self, input_bit, max_delay):
        self.delay = Signal(bits_for(max_delay))
        self.reset = Signal(1)

        self.input = Signal((input_bit, True))
        self.output = Signal((input_bit, True))

        registers = [Signal((input_bit, True)) for _ in range(max_delay)]

        self.comb += [registers[0].eq(self.input)]

        for idx, register in enumerate(registers):
            if idx < len(registers) - 1:
                next_register = registers[idx + 1]
                self.sync += [
                    If(self.reset, next_register.eq(0)).Else(
                        next_register.eq(register)
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
    Use `self.reset` to reset the calculation.
    """
    def __init__(self, width=14, N_points=8191):
        self.reset = Signal()

        self.input = Signal((width, True))
        self.delay_value = Signal(bits_for(N_points))

        sum_value_bits = bits_for(((2 ** width) - 1) * N_points)
        self.sum_value = Signal((sum_value_bits, True))
        delayed_sum = Signal((sum_value_bits, True))
        current_sum_diff = Signal((sum_value_bits + 1, True))
        self.output = Signal.like(current_sum_diff)

        # FIXME: max_delay should be in theory N_points but this makes simulation too hard.
        #        How to solve this?
        self.submodules.delayer = DynamicDelay(sum_value_bits, 20)

        self.sync += [
            If(self.reset, self.sum_value.eq(0),).Else(
                # not at start
                self.sum_value.eq(self.sum_value + self.input)
            )
        ]

        self.comb += [
            self.delayer.reset.eq(self.reset),
            self.delayer.delay.eq(self.delay_value),
            self.delayer.input.eq(self.sum_value),
            delayed_sum.eq(self.delayer.output),
            current_sum_diff.eq(self.sum_value - delayed_sum),
            self.output.eq(current_sum_diff)
        ]


class AutolockFPGA(Module, AutoCSR):
    def __init__(self, width=14, N_points=8191):
        self.at_start = Signal()

        # contains the index of the spectrum that is currently addressed
        counter = Signal(bits_for(N_points))

        self.input = Signal((width, True))
        self.time_scale = CSRStorage(bits_for(N_points))

        self.submodules.sum_diff_calculator = SumDiffCalculator(width, N_points)

        # FIXME: is 32 instructions maximum? Enforce this limit in client
        max_N_instructions = 32

        self.current_instruction_idx = Signal(bits_for(max_N_instructions))

        peak_height_bit = 14
        self.peak_heights = [
            CSRStorage(peak_height_bit, True, name="peak_height_%d" % idx)
            for idx in range(max_N_instructions)
        ]
        for idx, peak_height in enumerate(self.peak_heights):
            setattr(self, "peak_height_%d" % idx, peak_height)

        x_data_length_bit = 14
        self.wait_for = [
            CSRStorage(x_data_length_bit, name="wait_for_%d" % idx)
            for idx in range(max_N_instructions)
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

        sum_diff = Signal((len(self.sum_diff_calculator.output), True))
        sign_equal = Signal()
        over_threshold = Signal()
        waited_long_enough = Signal()

        abs_sum_diff = Signal.like(sum_diff)
        abs_current_peak_height = Signal.like(current_peak_height)


        self.comb += [
            self.sum_diff_calculator.reset.eq(self.at_start),
            self.sum_diff_calculator.input.eq(self.input),
            self.sum_diff_calculator.delay_value.eq(self.time_scale.storage),
            sum_diff.eq(self.sum_diff_calculator.output),
            sign_equal.eq((sum_diff > 0) == (current_peak_height > 0)),

            If(sum_diff >= 0,
                abs_sum_diff.eq(sum_diff)
            ).Else(
                abs_sum_diff.eq(-1 * sum_diff)),
            If(current_peak_height >= 0,
                abs_current_peak_height.eq(current_peak_height)
            ).Else(
                abs_current_peak_height.eq(-1 * current_peak_height)
            ),

            over_threshold.eq(abs_sum_diff >= abs_current_peak_height),
            waited_long_enough.eq(waited_for > current_wait_for),

        ]

        self.sync += [
            If(
                self.at_start,
                waited_for.eq(0),
                counter.eq(0),
                self.current_instruction_idx.eq(0),
            ).Else(
                # not at start
                counter.eq(counter + 1),
                If(
                    sign_equal & over_threshold & waited_long_enough,
                    self.current_instruction_idx.eq(self.current_instruction_idx + 1),
                    waited_for.eq(0),
                ).Else(waited_for.eq(waited_for + 1)),
            )
        ]


def get_lock_position_from_autolock_instructions_by_simulating_fpga(
    spectrum, description, time_scale, initial_spectrum
):
    result = {}
    def tb(dut):
        yield dut.at_start.eq(1)

        for description_idx, [wait_for, current_threshold] in enumerate(description):
            yield dut.peak_heights[description_idx].storage.eq(int(current_threshold))
            yield dut.wait_for[description_idx].storage.eq(int(wait_for))

        yield

        yield dut.at_start.eq(0)
        yield dut.time_scale.storage.eq(int(time_scale))

        for i in range(len(spectrum)):
            yield dut.input.eq(int(spectrum[i]))

            instruction_idx = yield dut.current_instruction_idx

            if instruction_idx >= len(description):
                result['index'] = i
                return

            yield


    dut = AutolockFPGA()
    run_simulation(
        dut, tb(dut), vcd_name="experimental_autolock_fpga_lock_position_finder.vcd"
    )

    return result.get('index')
