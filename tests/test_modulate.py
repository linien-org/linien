from pathlib import Path

import numpy as np
import pytest
from migen import Module, Signal, run_simulation

from gateware.logic.modulate import Demodulate, Modulate

VCD_DIR = Path(__file__).parent / "vcd"


def moving_average(a, n):
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1 :] / n


def block_average(a, n):
    iteration = 0
    average = []
    while len(a[iteration * n :]) >= n:
        block = a[iteration * n : (iteration + 1) * n]
        average.append(np.mean(block))
        iteration += 1

    return np.array(average)


factor = 5


@pytest.mark.slow
def test_modulate(plt):
    width = 16
    data = []
    phase = []
    demodulated = []
    cordic_out_2 = []

    amp = 2 ** (width - 2)
    frequency = (2 ** (width + 9)) - 1
    frequency_width = 32
    period = int((2 ** frequency_width) / frequency)
    print(period)

    def tb(combined):
        mod = combined.mod
        demod = combined.demod

        yield from mod.amp.write(amp)
        yield from mod.freq.write(frequency)

        for iteration in range(10):
            yield combined.phase_shift.eq(iteration * 7000)
            yield mod.amp.storage.eq(int(amp / (iteration + 1)))

            for i in range(period * factor):
                yield

                data.append((yield mod.y))
                phase.append((yield mod.phase))
                demodulated.append((yield demod.i))
                cordic_out_2.append((yield demod.cordic.yo >> 1))

    class Combined(Module):
        def __init__(self):
            self.submodules.mod = Modulate(width=width)
            self.submodules.demod = Demodulate(width=width)

            self.phase_shift = Signal(width)

            self.comb += [
                self.demod.x.eq(self.mod.y),
                self.demod.phase.eq(self.mod.phase + self.phase_shift),
            ]

    dut = Combined()
    run_simulation(dut, tb(dut), vcd_name=VCD_DIR / "modulate.vcd")

    """        """
    plt.plot(data, label="y")
    plt.plot(demodulated, label="demod")
    # plt.plot(phase, label='phase')
    averaged1 = block_average(demodulated, period * factor)
    plt.plot(averaged1, label="demod averaged")
    averaged2 = block_average(cordic_out_2, period * factor)
    plt.plot(averaged2, label="cordic_out_2 averaged")

    plt.plot(np.sqrt(averaged1 ** 2 + averaged2 ** 2), label="averaged+averaged")

    plt.legend()


if __name__ == "__main__":
    test_modulate()
