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

from pathlib import Path

import numpy as np
import pytest
from linien_server.autolock.robust import (
    calculate_autolock_instructions,
    get_lock_position_from_autolock_instructions,
)
from linien_server.autolock.utils import (
    crop_spectra_to_same_view,
    get_diff_at_time_scale,
    get_lock_region,
    get_time_scale,
    sum_up_spectrum,
)
from migen import run_simulation

from gateware.logic.autolock import RobustAutolock
from gateware.logic.autolock_utils import DynamicDelay, SumDiffCalculator

VCD_DIR = Path(__file__).parent / "vcd"
FPGA_DELAY_SUMDIFF_CALCULATOR = 2

RNG = np.random.default_rng(seed=0)


def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def as_int(array):
    """FPGA calculates using ints, so do we."""
    return np.round(array).astype(np.int64)


def atomic_spectrum(noise_level):
    x = np.linspace(-30, 30, 512)
    central_peak = peak(x) * 2048
    smaller_peaks = (peak(x - 10) * 1024) - (peak(x + 10) * 1024)
    target_idxs = (328, 350)
    return (
        as_int(
            central_peak + smaller_peaks + (RNG.standard_normal(len(x)) * noise_level)
        ),
        target_idxs,
    )


def pfd_spectrum(noise_level):
    x = np.linspace(-30, 30, 512)
    y = x * 1000
    y[y > 3000] = 3000
    y[y < -3000] = -3000
    target_idxs = (220, 300)
    return as_int(y + (RNG.standard_normal(len(x)) * noise_level)), target_idxs


def add_noise(spectrum, level):
    return as_int(spectrum + (RNG.standard_normal(len(spectrum)) * level))


def add_jitter(spectrum, level=None, exact_value=None):
    assert (level is not None) or (exact_value is not None)
    if exact_value is None:
        exact_value = int(round(RNG.standard_normal() * level))

    shift = exact_value
    return np.roll(spectrum, shift)


@pytest.mark.slow
def test_get_description(plt, debug=True):
    def get_lock_position_from_autolock_instructions_by_simulating_fpga(
        spectrum, description, time_scale, initial_spectrum, final_wait_time
    ):
        """
        This function simulated the behavior of `RobustAutolock` on FPGA and allows to
        find out whether FPGA would lock to the correct point.
        """
        result = {}

        def tb(dut):
            yield dut.sweep_up.eq(1)
            yield dut.request_lock.eq(1)
            yield dut.at_start.eq(1)
            yield dut.writing_data_now.eq(1)

            yield dut.N_instructions.storage.eq(len(description))
            yield dut.final_wait_time.storage.eq(final_wait_time)

            for description_idx, [wait_for, current_threshold] in enumerate(
                description
            ):
                yield dut.peak_heights[description_idx].storage.eq(
                    int(current_threshold)
                )
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

        dut = RobustAutolock()
        run_simulation(
            dut,
            tb(dut),
            vcd_name=VCD_DIR / "experimental_autolock_fpga_lock_position_finder.vcd",
        )

        return result.get("index")

    for sign_spectrum_multiplicator in (1, -1):
        for spectrum_generator in (pfd_spectrum, atomic_spectrum):
            spectrum, target_idxs = spectrum_generator(0)
            spectrum *= sign_spectrum_multiplicator

            if debug:
                plt.plot(spectrum)

            jitters = [
                0 if i == 0 else int(round(RNG.standard_normal() * 50))
                for i in range(10)
            ]

            spectra_with_jitter = [
                add_jitter(add_noise(spectrum, 100), exact_value=jitter).astype(
                    np.int64
                )
                for jitter in jitters
            ]

            description, final_wait_time, time_scale = calculate_autolock_instructions(
                spectra_with_jitter, target_idxs
            )

            lock_region = get_lock_region(spectrum, target_idxs)

            lock_positions = []

            for spectrum_idx, [jitter, spectrum] in enumerate(
                zip(jitters, spectra_with_jitter)
            ):
                lock_position = get_lock_position_from_autolock_instructions(
                    spectrum,
                    description,
                    time_scale,
                    spectra_with_jitter[0],
                    final_wait_time,
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

                print("lock_positions", lock_position, lock_position_fpga)
                assert abs(lock_position - lock_position_fpga) <= 1

                lock_position_corrected = lock_position - jitter

                lock_positions.append(lock_position_corrected)

                if debug:
                    if spectrum_idx == 0:
                        kwargs = {"label": "lock ended up here"}
                    else:
                        kwargs = {}
                    plt.axvline(lock_positions[-1], color="green", alpha=0.5, **kwargs)

                assert lock_region[0] <= lock_position_corrected <= lock_region[1]

            if debug:
                plt.plot(spectra_with_jitter[0])
                # plt.plot(get_diff_at_time_scale(sum_up_spectrum(spectra[0]), time_scale))  # noqa: E501
                plt.axvspan(
                    lock_region[0],
                    lock_region[1],
                    alpha=0.2,
                    color="yellow",
                    label="its okay to end up in this region",
                )
                plt.axvspan(
                    target_idxs[0],
                    target_idxs[1],
                    alpha=0.2,
                    color="red",
                    label="user selected region",
                )

                plt.legend()


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
    run_simulation(
        dut, tb(dut), vcd_name=VCD_DIR / "experimental_autolock_dynamic_delay.vcd"
    )


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
        dut, tb(dut), vcd_name=VCD_DIR / "experimental_autolock_sum_diff_calculator.vcd"
    )


def test_sum_diff_calculator2():
    spectrum = pfd_spectrum(0)[0]

    delay = 60
    out_fpga = []

    def tb(dut):
        yield dut.restart.eq(0)
        yield dut.delay_value.eq(delay)
        yield dut.writing_data_now.eq(1)

        for point in spectrum:
            yield dut.input.eq(int(point))
            yield
            out = yield dut.output
            out_fpga.append(out)

    dut = SumDiffCalculator(14, 8192)
    run_simulation(
        dut, tb(dut), vcd_name=VCD_DIR / "experimental_autolock_sum_diff_calculator.vcd"
    )

    summed = sum_up_spectrum(spectrum)
    summed_xscaled = get_diff_at_time_scale(summed, delay)

    # plt.plot(out_fpga[1:])
    # plt.plot(summed_xscaled)
    # plt.show()
    assert out_fpga[1:] == summed_xscaled[:-1]


@pytest.mark.slow
def test_compare_sum_diff_calculator_implementations(plt, debug=True):
    for iteration in (0, 1):
        if iteration == 1:
            spectrum, target_idxs = atomic_spectrum(0)
            time_scale = get_time_scale(spectrum, target_idxs)
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
            dut,
            tb(dut),
            vcd_name=VCD_DIR / "experimental_autolock_fpga_lock_position_finder.vcd",
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

            plt.plot(
                summed_xscaled[:-FPGA_DELAY_SUMDIFF_CALCULATOR],
                label="normal calculation",
            )
            plt.plot(
                summed_fpga["summed_xscaled"][FPGA_DELAY_SUMDIFF_CALCULATOR:],
                label="FPGA calculation",
            )
            plt.legend()

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
        dut,
        tb(dut),
        vcd_name=VCD_DIR / "experimental_autolock_fpga_lock_position_finder.vcd",
    )


def test_crop_spectra_to_same_view(plt):
    spectra_to_test = (
        [np.roll(atomic_spectrum(0)[0], -i * 10) for i in range(10)],
        [np.roll(atomic_spectrum(0)[0], i * 10) for i in range(10)],
        [add_jitter(atomic_spectrum(0)[0], 50 if i > 0 else 0) for i in range(10)],
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

            plt.plot(cropped_spectrum)


if __name__ == "__main__":
    test_dynamic_delay()
    test_crop_spectra_to_same_view()
    test_compare_sum_diff_calculator_implementations()
    test_sum_diff_calculator()
    test_sum_diff_calculator2()
    test_fpga_lock_position_finder()
    test_get_description(debug=True)
