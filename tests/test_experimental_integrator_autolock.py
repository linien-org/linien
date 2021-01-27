import numpy as np
from matplotlib import pyplot as plt
from scipy.signal import correlate, resample
from migen import (
    Signal,
    Module,
    Instance,
    ClockSignal,
    ResetSignal,
    Array,
    Record,
    ClockDomain,
    ClockDomainsRenamer,
    If,
    bits_for,
    run_simulation,
)
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus


TARGET_IDXS = (328, 350)


class LockPositionNotFound(Exception):
    pass


class UnableToFindDescription(Exception):
    pass


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(noise_level):
    x = np.linspace(-30, 30, 512)
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return central_peak + smaller_peaks + (np.random.randn(len(x)) * noise_level)


def add_noise(spectrum, level):
    return spectrum + (np.random.randn(len(spectrum)) * level)


def add_jitter(spectrum, level):
    shift = int(round(np.random.randn() * level))
    print("shift", shift)
    return np.roll(spectrum, shift)


def get_lock_region(spectrum, target_idxs):
    part = spectrum[target_idxs[0] : target_idxs[1]]
    return tuple(
        sorted([target_idxs[0] + np.argmin(part), target_idxs[0] + np.argmax(part)])
    )


def get_x_scale(spectrum, target_idxs):
    part = spectrum[target_idxs[0] : target_idxs[1]]
    return np.abs(np.argmin(part) - np.argmax(part))


def sum_up_spectrum(spectrum):
    sum_ = 0
    summed = []

    for value in spectrum:
        summed.append(sum_ + value)
        sum_ += value

    return summed


def get_diff_at_x_scale(summed, xscale):
    new = []

    for idx, value in enumerate(summed):
        if idx < xscale:
            old = 0
        else:
            old = summed[idx - xscale]

        new.append(value - old)

    return new


def sign(value):
    return 1 if value >= 1 else -1


def get_target_peak(summed_xscaled, target_idxs):
    selected_region = summed_xscaled[target_idxs[0] : target_idxs[1]]
    # in the selected region, we may have 1 minimum and one maximum
    # we know that we are interested in the "left" extremum --> sort extrema
    # by index and take the first one
    extremum = np.min([np.argmin(selected_region), np.argmax(selected_region)])
    current_idx = target_idxs[0] + extremum
    return current_idx


def get_all_peaks(summed_xscaled, target_idxs):
    current_idx = get_target_peak(summed_xscaled, target_idxs)

    peaks = []

    peaks.append((current_idx, summed_xscaled[current_idx]))

    while True:
        if current_idx == 0:
            break
        current_idx -= 1

        value = summed_xscaled[current_idx]
        last_peak_position, last_peak_height = peaks[-1]

        if sign(last_peak_height) == sign(value):
            if np.abs(value) > np.abs(last_peak_height):
                peaks[-1] = (current_idx, value)
        else:
            peaks.append((current_idx, value))

    return peaks


class DynamicDelay(Module):
    def __init__(self, input_bit, max_delay):
        self.delay = Signal(bits_for(max_delay))
        self.at_start = Signal(1)

        self.input = Signal((input_bit, True))
        self.output = Signal((input_bit, True))

        registers = [Signal((input_bit, True)) for _ in range(max_delay)]

        self.comb += [registers[0].eq(self.input)]
        for idx, register in enumerate(registers):
            if idx < len(registers) - 1:
                next_register = registers[idx + 1]
                self.sync += [
                    If(self.at_start, next_register.eq(0)).Else(
                        next_register.eq(register)
                    )
                ]

        self.comb += [self.output.eq(Array(registers)[self.delay])]


class SumDiffCalculator(Module):
    def __init__(self, width=14, N_points=8191):
        self.at_start = Signal()

        self.value = Signal((width, True))
        self.delay_value = Signal(bits_for(N_points))

        sum_value_bits = bits_for(((2 ** width) - 1) * N_points)
        sum_value = Signal((sum_value_bits, True))
        delayed_sum = Signal((sum_value_bits, True))
        self.current_sum_diff = Signal((sum_value_bits + 1, True))

        self.submodules.delayer = DynamicDelay(sum_value_bits, bits_for(N_points))

        self.sync += [
            If(self.at_start, sum_value.eq(0),).Else(
                # not at start
                sum_value.eq(sum_value + self.value)
            )
        ]

        self.comb += [
            self.delayer.at_start.eq(self.at_start),
            self.delayer.delay.eq(self.delay_value),
            self.delayer.input.eq(sum_value),
            delayed_sum.eq(self.delayer.output),
            self.current_sum_diff.eq(sum_value - delayed_sum),
        ]


class FPGALockPositionFinder(Module):
    def __init__(self, width=14, N_points=8191):
        self.at_start = Signal()
        counter = Signal(bits_for(N_points))

        self.value = Signal((width, True))
        self.x_scale = CSRStorage(bits_for(N_points))

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

        def abs_signal(signal):
            return If(signal > 0, signal).Else(-1 * signal)

        sum_diff = Signal((len(self.sum_diff_calculator.current_sum_diff), True))
        sign_equal = Signal()
        over_threshold = Signal()
        waited_long_enough = Signal()

        abs_sum_diff = Signal.like(sum_diff)
        abs_current_peak_height = Signal.like(current_peak_height)


        self.comb += [
            self.sum_diff_calculator.at_start.eq(self.at_start),
            self.sum_diff_calculator.value.eq(self.value),
            self.sum_diff_calculator.delay_value.eq(self.x_scale.storage),
            sum_diff.eq(self.sum_diff_calculator.current_sum_diff),
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

        self.foo = Signal()
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


def get_lock_position_from_description_fpga(
    spectrum, description, x_scale, initial_spectrum
):
    pass


def get_lock_position_from_description(
    spectrum, description, x_scale, initial_spectrum
):
    summed = sum_up_spectrum(spectrum)
    summed_xscaled = get_diff_at_x_scale(summed, x_scale)

    description_idx = 0

    last_detected_peak = 0

    for idx, value in enumerate(summed_xscaled):
        wait_for, current_threshold = description[description_idx]

        if (
            sign(value) == sign(current_threshold)
            and abs(value) >= abs(current_threshold)
            # TODO: this .9 factor is very arbitrary. also: first peak should have special treatment bc of horizontal jitter
            and idx - last_detected_peak > wait_for * 0.9
        ):
            description_idx += 1
            last_detected_peak = idx

            if description_idx == len(description):
                # this was the last peak!
                return idx

    """plt.clf()
    # plt.plot(spectrum, color="blue", alpha=0.5)
    plt.plot(
        get_diff_at_x_scale(sum_up_spectrum(spectrum), x_scale),
        color="green",
        alpha=0.5,
        label="to test",
    )
    # plt.plot(initial_spectrum, color="red", alpha=0.5)
    plt.plot(
        get_diff_at_x_scale(sum_up_spectrum(initial_spectrum), x_scale),
        color="orange",
        alpha=0.5,
        label="initial",
    )

    plt.legend()
    plt.grid()
    plt.show()"""
    raise LockPositionNotFound()


def get_description(spectra, target_idxs):
    # FIXME: TODO: y shift such that initial line always has + and - peak. Is this really needed?
    x_scale = int(
        round(np.mean([get_x_scale(spectrum, target_idxs) for spectrum in spectra]))
    )
    print(f"x scale is {x_scale}")
    for tolerance_factor in [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]:
        print("TOLERANCE", tolerance_factor)
        prepared_spectrum = get_diff_at_x_scale(sum_up_spectrum(spectra[0]), x_scale)
        peaks = get_all_peaks(prepared_spectrum, target_idxs)

        y_scale = peaks[0][1]
        peaks_filtered = [
            (peak_position, peak_height * tolerance_factor)
            for peak_position, peak_height in peaks
        ]
        # it is important to do the filtering that happens here after the previous
        # line as the previous line shrinks the values
        peaks_filtered = [
            (peak_position, peak_height)
            for peak_position, peak_height in peaks_filtered
            if abs(peak_height) > abs(y_scale * (1 - tolerance_factor))
        ]

        # now find out how much we have to wait in the end (because we detect the peak
        # too early because our threshold is too low)
        target_peak_described_height = peaks_filtered[0][1]
        target_peak_idx = get_target_peak(prepared_spectrum, TARGET_IDXS)
        current_idx = target_peak_idx
        while True:
            current_idx -= 1
            if np.abs(prepared_spectrum[current_idx]) < np.abs(
                target_peak_described_height
            ):
                break
        final_wait_time = target_peak_idx - current_idx
        print(f"final wait time is {final_wait_time} samples")

        description = []

        last_peak_position = 0
        for peak_position, peak_height in list(reversed(peaks_filtered)):
            description.append(((peak_position - last_peak_position), peak_height))
            last_peak_position = peak_position

        # test whether description works fine for every recorded spectrum
        does_work = True
        for spectrum in spectra:
            lock_region = get_lock_region(spectrum, target_idxs)

            try:
                lock_position = (
                    get_lock_position_from_description(
                        spectrum,
                        description,
                        x_scale,
                        spectra[0],
                    )
                    + final_wait_time
                )
                if not lock_region[0] <= lock_position <= lock_region[1]:
                    raise LockPositionNotFound()

            except LockPositionNotFound:
                does_work = False

        if does_work:
            break
    else:
        raise UnableToFindDescription()

    return description, final_wait_time, x_scale


def test_get_description():
    spectrum = spectrum_for_testing(0)

    spectra_with_jitter = [
        add_jitter(add_noise(spectrum, 100), 100 if _ > 0 else 0) for _ in range(10)
    ]
    spectra = []

    for idx, spectrum in enumerate(spectra_with_jitter):
        if idx == 0:
            shift = 0
        else:
            shift = np.argmax(correlate(spectra[0], spectrum))
            print("detected", -1 * (shift - len(spectrum)))

        # FIXME: don't use roll but crop
        spectra.append(np.roll(spectrum, shift))
        # plt.plot(spectra[-1])

    # plt.show()
    # asd
    description, final_wait_time, x_scale = get_description(spectra, TARGET_IDXS)

    print("DESCRIPTION", description)

    lock_positions = []

    for spectrum in spectra:
        lock_positions.append(
            get_lock_position_from_description(
                spectrum, description, x_scale, spectra[0]
            )
            + final_wait_time
        )

        plt.axvline(lock_positions[-1], color="green", alpha=0.5)

    plt.plot(spectra[0])
    # plt.plot(get_diff_at_x_scale(sum_up_spectrum(spectra[0]), x_scale))
    plt.axvspan(TARGET_IDXS[0], TARGET_IDXS[1], alpha=0.2, color="red")

    plt.legend()
    plt.show()


def test_dynamic_delay():
    def tb(dut):
        yield dut.input.eq(1)
        yield dut.delay.eq(10)

        for i in range(10):
            yield

            out = yield dut.output
            assert out == 0

        yield
        out = yield dut.output
        assert out == 1

    dut = DynamicDelay(14 + 14, 8192)
    run_simulation(dut, tb(dut), vcd_name="experimental_autolock_dynamic_delay.vcd")


def test_sum_diff_calculator():
    def tb(dut):
        value = 5
        delay = 10
        yield dut.at_start.eq(0)
        yield dut.value.eq(value)
        yield dut.delay_value.eq(delay)

        for i in range(20):
            yield

            out = yield dut.current_sum_diff

            if i <= 10:
                assert out == i * value
            else:
                assert out == delay * value

        yield dut.value.eq(-5)
        for i in range(20):
            yield

            out = yield dut.current_sum_diff

        assert out == -50

        yield dut.at_start.eq(1)
        yield
        yield dut.at_start.eq(0)
        yield
        out = yield dut.current_sum_diff
        assert out == 0

        yield
        out = yield dut.current_sum_diff
        assert out != 0

    dut = SumDiffCalculator(14, 8192)
    run_simulation(
        dut, tb(dut), vcd_name="experimental_autolock_sum_diff_calculator.vcd"
    )


def test_fpga_lock_position_finder():
    def tb(dut):
        for iteration in range(2):
            yield dut.at_start.eq(1)
            yield

            yield dut.at_start.eq(0)
            yield dut.x_scale.storage.eq(5)
            heights = [6000, 7000, -100]
            yield dut.wait_for_0.storage.eq(0)
            yield dut.peak_height_0.storage.eq(heights[0])

            yield dut.wait_for_1.storage.eq(10)
            yield dut.peak_height_1.storage.eq(heights[1])

            yield dut.wait_for_2.storage.eq(10)
            yield dut.peak_height_2.storage.eq(heights[2])

            yield dut.value.eq(1000)

            # with a value of 1000 and xscale of 5 diff is max at 5000
            # --> we never reach the threshold and instruction_idx should remain 0
            for i in range(20):
                yield
                # diff = yield dut.sum_diff_calculator.current_sum_diff
                instruction_idx = yield dut.current_instruction_idx
                assert instruction_idx == 0

            # increasing value to 2000 --> diff is 10000 after 5 cycles
            # (over threshold)
            yield dut.value.eq(2000)

            for i in range(30):
                yield
                diff = yield dut.sum_diff_calculator.current_sum_diff
                instruction_idx = yield dut.current_instruction_idx

                # check that once we are over threshold, instruction index increases
                # also check that wait_time is used before second instruction is also
                # fulfilled
                if diff > heights[0]:
                    if i < 14:
                        assert instruction_idx == 1
                    else:
                        assert instruction_idx == 2
                else:
                    assert instruction_idx == 0

            # check that third instruction is never fulfilled because sign doesn't match
            for i in range(100):
                yield
                instruction_idx = yield dut.current_instruction_idx
                assert instruction_idx == 2

            # check that negative instruction is fulfilled
            # for that first go to 0
            for i in range(5):
                yield dut.value.eq(0)
                yield

            # now go to negative range
            yield dut.value.eq(-30)

            for i in range(100):
                yield
                instruction_idx = yield dut.current_instruction_idx

                if i < 5:
                    assert instruction_idx == 2
                else:
                    assert instruction_idx == 3


    dut = FPGALockPositionFinder()
    run_simulation(
        dut, tb(dut), vcd_name="experimental_autolock_fpga_lock_position_finder.vcd"
    )


if __name__ == "__main__":
    # test_get_description()
    # test_dynamic_delay()
    # test_sum_diff_calculator()
    test_fpga_lock_position_finder()