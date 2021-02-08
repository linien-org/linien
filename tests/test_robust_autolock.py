from linien.server.autolock.utils import (
    crop_spectra_to_same_view,
    get_diff_at_time_scale,
    get_time_scale,
    sum_up_spectrum,
)
from linien.server.autolock.robust import (
    calculate_autolock_instructions,
    get_lock_position_from_autolock_instructions,
)
from gateware.logic.autolock_utils import DynamicDelay, SumDiffCalculator
from gateware.logic.autolock import (
    RobustAutolock,
    get_lock_position_from_autolock_instructions_by_simulating_fpga,
)
import numpy as np
from matplotlib import pyplot as plt
from migen import run_simulation


TARGET_IDXS = (328, 350)
FPGA_DELAY_SUMDIFF_CALCULATOR = 2


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def as_int(array):
    """FPGA calculates using ints, so do we."""
    return np.round(array).astype(np.int64)


def spectrum_for_testing(noise_level):
    x = np.linspace(-30, 30, 512)
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    return as_int(
        central_peak + smaller_peaks + (np.random.randn(len(x)) * noise_level)
    )


def add_noise(spectrum, level):
    return as_int(spectrum + (np.random.randn(len(spectrum)) * level))


def add_jitter(spectrum, level=None, exact_value=None):
    assert (level is not None) or (exact_value is not None)
    if exact_value is None:
        exact_value = int(round(np.random.randn() * level))

    shift = exact_value
    return np.roll(spectrum, shift)


def test_get_description(debug=False):
    spectrum = spectrum_for_testing(0)

    jitters = [0 if i == 0 else int(round(np.random.randn() * 50)) for i in range(10)]

    spectra_with_jitter = [
        add_jitter(add_noise(spectrum, 100), exact_value=jitter).astype(np.int64)
        for jitter in jitters
    ]

    description, final_wait_time, time_scale = calculate_autolock_instructions(
        spectra_with_jitter, TARGET_IDXS
    )

    lock_positions = []

    for jitter, spectrum in zip(jitters, spectra_with_jitter):
        lock_position = get_lock_position_from_autolock_instructions(
            spectrum, description, time_scale, spectra_with_jitter[0], final_wait_time
        )
        lock_position_fpga = (
            get_lock_position_from_autolock_instructions_by_simulating_fpga(
                spectrum,
                description,
                time_scale,
                spectra_with_jitter[0],
                int(final_wait_time),
            )
        )

        assert lock_position == lock_position_fpga

        lock_position_corrected = lock_position - jitter

        lock_positions.append(lock_position_corrected)

        if debug:
            plt.axvline(lock_positions[-1], color="green", alpha=0.5)

        assert TARGET_IDXS[0] <= lock_position_corrected <= TARGET_IDXS[1]

    if debug:
        plt.plot(spectra_with_jitter[0])
        # plt.plot(get_diff_at_time_scale(sum_up_spectrum(spectra[0]), time_scale))
        plt.axvspan(TARGET_IDXS[0], TARGET_IDXS[1], alpha=0.2, color="red")

        plt.legend()
        plt.show()


def test_dynamic_delay():
    def tb(dut):
        yield dut.input.eq(1)
        yield dut.delay.eq(10)
        yield dut.writing_data_now.eq(1)

        for i in range(10):
            yield

            out = yield dut.output
            assert out == 0

        yield
        out = yield dut.output
        assert out == 1

    dut = DynamicDelay(14 + 14, max_delay=8191)
    run_simulation(dut, tb(dut), vcd_name="experimental_autolock_dynamic_delay.vcd")


def test_sum_diff_calculator():
    def tb(dut):
        value = 5
        delay = 10
        yield dut.restart.eq(0)
        yield dut.input.eq(value)
        yield dut.delay_value.eq(delay)
        yield dut.writing_data_now.eq(1)

        for i in range(20):
            yield

            out = yield dut.output

            if i <= 10:
                assert out == i * value
            else:
                assert out == delay * value

        yield dut.input.eq(-5)
        for i in range(20):
            yield

            out = yield dut.output

        assert out == -50

        yield dut.restart.eq(1)
        yield
        yield dut.restart.eq(0)
        yield
        out = yield dut.output
        assert out == 0

        yield
        out = yield dut.output
        assert out != 0

    dut = SumDiffCalculator(14, 8192)
    run_simulation(
        dut, tb(dut), vcd_name="experimental_autolock_sum_diff_calculator.vcd"
    )


def test_compare_sum_diff_calculator_implementations(debug=False):
    for iteration in (0, 1):
        if iteration == 1:
            spectrum = spectrum_for_testing(0)
            time_scale = get_time_scale(spectrum, TARGET_IDXS)
        else:
            spectrum = [1 * i for i in range(1000)]
            time_scale = 5

        summed = sum_up_spectrum(spectrum)
        summed_xscaled = get_diff_at_time_scale(summed, time_scale)

        summed_fpga = {"summed_xscaled": [], "summed": []}

        def tb(dut):
            yield dut.request_lock.eq(1)
            yield dut.at_start.eq(1)
            yield dut.writing_data_now.eq(1)

            yield dut.at_start.eq(0)
            yield dut.time_scale.storage.eq(int(time_scale))

            for i in range(len(spectrum)):
                yield dut.input.eq(int(spectrum[i]))

                sum_diff = yield dut.sum_diff_calculator.output
                sum = yield dut.sum_diff_calculator.sum_value
                summed_fpga["summed_xscaled"].append(sum_diff)
                summed_fpga["summed"].append(sum)

                yield

        dut = RobustAutolock()
        run_simulation(
            dut, tb(dut), vcd_name="experimental_autolock_fpga_lock_position_finder.vcd"
        )

        if debug:
            plt.plot(
                summed[:-FPGA_DELAY_SUMDIFF_CALCULATOR], label="normal calculation"
            )
            plt.plot(
                summed_fpga["summed"][FPGA_DELAY_SUMDIFF_CALCULATOR:],
                label="FPGA calculation",
            )
            plt.legend()
            plt.show()

            plt.plot(
                summed_xscaled[:-FPGA_DELAY_SUMDIFF_CALCULATOR],
                label="normal calculation",
            )
            plt.plot(
                summed_fpga["summed_xscaled"][FPGA_DELAY_SUMDIFF_CALCULATOR:],
                label="FPGA calculation",
            )
            plt.legend()
            plt.show()

        assert (
            summed[:-FPGA_DELAY_SUMDIFF_CALCULATOR]
            == summed_fpga["summed"][FPGA_DELAY_SUMDIFF_CALCULATOR:]
        )
        assert (
            summed_xscaled[:-FPGA_DELAY_SUMDIFF_CALCULATOR]
            == summed_fpga["summed_xscaled"][FPGA_DELAY_SUMDIFF_CALCULATOR:]
        )


def test_fpga_lock_position_finder():
    def tb(dut: RobustAutolock):
        yield dut.sweep_up.eq(1)

        for iteration in range(2):
            print("iteration", iteration)
            yield dut.request_lock.eq(1)
            yield dut.at_start.eq(1)
            yield dut.writing_data_now.eq(1)

            heights = [6000, 7000, -100, 10000]
            yield dut.N_instructions.storage.eq(len(heights))

            yield

            yield dut.at_start.eq(0)
            yield dut.time_scale.storage.eq(5)
            yield dut.wait_for_0.storage.eq(0)
            yield dut.peak_height_0.storage.eq(heights[0])

            yield dut.wait_for_1.storage.eq(10)
            yield dut.peak_height_1.storage.eq(heights[1])

            yield dut.wait_for_2.storage.eq(10)
            yield dut.peak_height_2.storage.eq(heights[2])

            yield dut.wait_for_3.storage.eq(10)
            yield dut.peak_height_3.storage.eq(heights[3])

            yield dut.input.eq(1000)

            # with a value of 1000 and xscale of 5 diff is max at 5000
            # --> we never reach the threshold and instruction_idx should remain 0
            for i in range(20):
                yield
                # diff = yield dut.sum_diff_calculator.output
                instruction_idx = yield dut.current_instruction_idx
                assert instruction_idx == 0

            # increasing value to 2000 --> diff is 10000 after 5 cycles
            # (over threshold)
            yield dut.input.eq(2000)

            for i in range(30):
                yield
                diff = yield dut.sum_diff_calculator.output
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
                yield dut.input.eq(0)
                yield

            # now go to negative range
            yield dut.input.eq(-30)

            for i in range(100):
                yield
                instruction_idx = yield dut.current_instruction_idx

                if i < 5:
                    assert instruction_idx == 2
                else:
                    assert instruction_idx == 3

    dut = RobustAutolock()
    run_simulation(
        dut, tb(dut), vcd_name="experimental_autolock_fpga_lock_position_finder.vcd"
    )


def test_crop_spectra_to_same_view():
    spectra_to_test = (
        [np.roll(spectrum_for_testing(0), -i * 10) for i in range(10)],
        [np.roll(spectrum_for_testing(0), i * 10) for i in range(10)],
        [add_jitter(spectrum_for_testing(0), 50 if i > 0 else 0) for i in range(10)],
    )

    for idx, spectra in enumerate(spectra_to_test):
        cropped_spectra, crop_left = crop_spectra_to_same_view(spectra)
        if idx == 0:
            assert crop_left == 90
        elif idx == 1:
            assert crop_left == 0

        assert len(cropped_spectra) == len(spectra)

        for cropped_spectrum in cropped_spectra:
            assert np.all(cropped_spectrum == cropped_spectra[0])

            # plt.plot(cropped_spectrum)
        # plt.show()


if __name__ == "__main__":
    test_dynamic_delay()
    test_crop_spectra_to_same_view()
    test_compare_sum_diff_calculator_implementations()
    test_sum_diff_calculator()
    test_fpga_lock_position_finder()
    test_get_description(debug=False)
