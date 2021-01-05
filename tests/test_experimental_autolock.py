import numpy as np
from matplotlib import pyplot as plt
from migen import Signal, Module, Instance, ClockSignal, ResetSignal, Array, Record, ClockDomain, ClockDomainsRenamer, If, bits_for
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus


TARGET_IDXS = (328, 350)
DEFAULT_SCALE_FACTOR = .5
COND_LT = 0
COND_GT = 1

def peak(x):
    return np.exp(-np.abs(x)) * np.sin(x)


def spectrum_for_testing(noise_level):
    x = np.linspace(-30, 30, 512)
    central_peak = (peak(x) * 2048)
    smaller_peaks = (peak(x-10) * 1024) - (peak(x+10) * 1024)
    return central_peak + smaller_peaks + (np.random.randn(len(x)) * noise_level)


def get_zero_crossing_idx(spectrum, target_idxs):
    zero_crossing_idx = target_idxs[0] + np.argmin(np.abs(spectrum[target_idxs[0]:target_idxs[1]]))
    return zero_crossing_idx


def test_get_zero_crossing_idx():
    spectrum = spectrum_for_testing(0)
    zero_crossing_idx = get_zero_crossing_idx(spectrum, TARGET_IDXS)
    assert TARGET_IDXS[1] > zero_crossing_idx > TARGET_IDXS[0]


def get_scale(spectrum, target_idxs):
    zero_crossing_idx = get_zero_crossing_idx(spectrum, target_idxs)

    left_part_of_target = spectrum[target_idxs[0]:zero_crossing_idx]
    highest_idx = target_idxs[0] + np.argmax(np.abs(left_part_of_target))
    scale = spectrum[highest_idx]

    return scale * DEFAULT_SCALE_FACTOR


def test_get_scale():
    spectrum = spectrum_for_testing(0)
    scale = get_scale(spectrum, TARGET_IDXS)
    assert np.abs(-(330*DEFAULT_SCALE_FACTOR) - scale) < .1
    scale_neg = get_scale(-spectrum, TARGET_IDXS)
    assert scale_neg == -1 * scale

def get_description(spectrum, target_idxs):
    zero_crossing_idx = get_zero_crossing_idx(spectrum, target_idxs)
    scale = get_scale(spectrum, target_idxs)

    description = []

    idx = zero_crossing_idx
    current_condition = None
    condition_counter = None
    description_part_finished = False

    while True:
        if idx == -1:
            description_part_finished = True
        else:
            value = spectrum[idx]

            if current_condition is not None:
                # check whether current condition matches
                if current_condition == COND_LT:
                    matches = np.abs(value) <= np.abs(scale)
                else:
                    matches = np.abs(value) > np.abs(scale)

                if matches:
                    condition_counter += 1

                else:
                    description_part_finished = True

        if description_part_finished:
            description.append(
                [current_condition, condition_counter]
            )
            current_condition = None
            condition_counter = None

        if idx == -1:
            break
        else:
            should_generate_new_condition = current_condition is None

            if should_generate_new_condition:
                if np.abs(value) <= np.abs(scale):
                    current_condition = COND_LT
                else:
                    # TODO: also implement sign?
                    current_condition = COND_GT

                condition_counter = 1
                description_part_finished = False

            idx -= 1

    return list(reversed(description))


class Tester(Module):
    def __init__(self):
        self.scale = CSRStorage(14)
        # FIXME: is 32 instructions maximum? Enforce this limit in client
        max_N_instructions = 32
        self.instructions = CSRStorage(max_N_instructions)
        self.current_instruction_idx = Signal(bits_for(max_N_instructions))
        # TODO: < 14 bit is possible, but how much?
        instruction_length_bit = 14
        self.instruction_lengths = [
            CSRStorage(instruction_length_bit)
            for idx in range(max_N_instructions)
        ]
        for idx, il in enumerate(self.instruction_lengths):
            setattr(self, 'instruction_length_%d' % idx, il)

        current_instruction = Signal(1)
        current_instruction_length = Signal(instruction_length_bit)

        self.comb += [
            current_instruction_length.eq(
                self.instruction_lengths[self.current_instruction_idx]
            ),
            current_instruction.eq(
                self.instructions[self.current_instruction_idx]
            )
        ]


        condition_fulfilled = Signal(1)
        self.comb += [
            If(current_instruction == COND_GT,
                condition_fulfilled.eq(
                    abs(self.value) > abs(self.scale)
                )
            ).Else(
                condition_fulfilled.eq(
                    abs(self.value) <= abs(self.scale)
                )
            )
        ]


        self.failed = Signal()


        self.counter = Signal(14)

        self.value = Signal((14, True))

        self.at_start = Signal()

        self.sync += [
            If(self.at_start,
                self.failed.eq(0),
                self.counter.eq(0),
                self.current_instruction_idx.eq(0)
            ).Else(

                If(self.value > self.to_compare,
                    self.counter.eq(self.counter + 1)
                )
            )
        ]


def test_get_description():
    spectrum = spectrum_for_testing(0)
    scale = get_scale(spectrum, TARGET_IDXS)

    description = get_description(spectrum, TARGET_IDXS)
    print(description)

    idx = 0
    for condition, counter in description:
        for sign in (1, -1):
            plt.plot(
                [idx, idx+counter],
                [sign*condition*scale, sign*condition*scale]
            )
        idx += counter

    plt.plot(spectrum)
    plt.show()


if __name__ == '__main__':
    test_get_zero_crossing_idx()
    test_get_scale()
    test_get_description()
