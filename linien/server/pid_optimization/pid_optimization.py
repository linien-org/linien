# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
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

import pickle
import random
import string
from time import sleep, time

import numpy as np
from pylpsd import lpsd
from scipy import signal

from linien.common import PSD_ALGORITHM_LPSD, PSD_ALGORITHM_WELCH
from linien.server.optimization.engine import MultiDimensionalOptimizationEngine

ALL_DECIMATIONS = list(range(32))


def calculate_psd(sig, fs, algorithm):
    """
    Calculates the power spectral density.

    :param sig: The signal to calculate the PSD for.
    :param fs: The sampling frequency.
    :param algorithm: The PSD algorithm to use. Options are 'lpsd' and 'welch'.
    :return: One-sided power spectral density.
    """
    assert algorithm in [PSD_ALGORITHM_LPSD, PSD_ALGORITHM_WELCH]

    # at beginning or end of signal, we sometimes have more glitches --> ignore
    # them (200 points less @ 16384 points doesn't hurt much)
    sig = sig[100:-100]

    num_pts = 256
    window = "hann"  # passed to scipy.signal.get_window for welch and lpsd

    sig = sig.astype(np.float64)

    if algorithm == PSD_ALGORITHM_WELCH:
        f, Pxx = signal.welch(
            sig, fs, window=window, nperseg=num_pts, scaling="density"
        )
    elif algorithm == PSD_ALGORITHM_LPSD:
        fmin = fs / len(sig) * 10  # lowest frequency of interest
        fmax = fs / 20.0  # highest frequency of interest

        f, Pxx = lpsd(
            sig,
            fs,
            window=window,
            fmin=fmin,
            fmax=fmax,
            Jdes=256,
            Kmin=2,
            scaling="density",
        )
    return f, Pxx


def residual_freq_noise(dt, sig, algorithm):
    fs = 1 / dt

    f, psd = calculate_psd(sig, fs, algorithm)
    # we want to have it in counts / Sqrt[Hz], not in (counts**2) / Hz
    psd = np.sqrt(psd)

    return f, psd


def psds_to_fitness(psds_by_decimation):
    fitness = 0

    for decimation, psd_data in psds_by_decimation.items():
        f, psd = psd_data
        fitness += sum(psd)

    return fitness


def generate_curve_uuid():
    return "".join(random.choice(string.ascii_lowercase) for i in range(10))


class PSDAcquisition:
    def __init__(self, control, parameters, is_child=False):
        self.decimation_index = 0

        self.recorded_signals_by_decimation = {}
        self.recorded_psds_by_decimation = {}

        self.running = True
        self.parameters = parameters
        self.control = control

        self.is_child = is_child

    def run(self):
        try:
            self.uuid = generate_curve_uuid()
            self.set_decimation(ALL_DECIMATIONS[0])
            self.add_listeners()
            self.parameters.psd_acquisition_running.value = True
        except:
            self.cleanup()
            raise

    def add_listeners(self):
        self.parameters.acquisition_raw_data.on_change(
            self.react_to_new_signal, call_listener_with_first_value=False
        )

    def cleanup(self):
        self.running = False
        self.parameters.psd_acquisition_running.value = False

        self.parameters.acquisition_raw_data.remove_listener(self.react_to_new_signal)

        if not self.is_child:
            self.control.pause_acquisition()
            self.parameters.acquisition_raw_enabled.value = False
            self.parameters.acquisition_raw_filter_enabled.value = False

            self.control.exposed_write_registers()
            self.control.continue_acquisition()

    def react_to_new_signal(self, data_pickled):
        try:
            if not self.running or self.parameters.pause_acquisition.value:
                return

            data = pickle.loads(data_pickled)

            current_decimation = self.parameters.acquisition_raw_decimation.value
            print("recorded signal for decimation", current_decimation)
            print("recording took", time() - self.time_decimation_set, "s")
            self.recorded_signals_by_decimation[current_decimation] = data
            self.recorded_psds_by_decimation[current_decimation] = residual_freq_noise(
                1 / (125e6) * (2 ** (current_decimation)),
                data[0],
                algorithm=self.parameters.psd_algorithm.value,
            )

            # this means that measurement time increases by a factor of 16 after
            # each measurement
            self.decimation_index += 4

            complete = (
                self.decimation_index
                > self.parameters.psd_acquisition_max_decimation.value
            )

            self.publish_psd_data(complete)

            if not complete:
                new_decimation = self.decimation_index
                print("set new decimation", new_decimation)
                self.set_decimation(new_decimation)
            else:
                self.cleanup()

        except:
            self.cleanup()
            raise

    def publish_psd_data(self, complete):
        data_pickled = pickle.dumps(
            {
                "uuid": self.uuid,
                "time": time(),
                "p": self.parameters.p.value,
                "i": self.parameters.i.value,
                "d": self.parameters.d.value,
                "signals": self.recorded_signals_by_decimation,
                "psds": self.recorded_psds_by_decimation,
                "fitness": psds_to_fitness(self.recorded_psds_by_decimation),
                "complete": complete,
            }
        )
        self.parameters.psd_data_partial.value = data_pickled
        if complete:
            # we ave an extra parameter for complete psd data becaue partial
            # psd data may change quickly. This makes it possible that someone
            # listening to partial psd data may miss the complete data set because
            # a new partial trace is being recorded.
            self.parameters.psd_data_complete.value = data_pickled

    def set_decimation(self, decimation):
        self.time_decimation_set = time()
        self.control.pause_acquisition()
        self.parameters.acquisition_raw_decimation.value = decimation
        self.parameters.acquisition_raw_enabled.value = True

        # lowpass filter for preventing alias effects
        self.parameters.acquisition_raw_filter_enabled.value = True
        self.parameters.acquisition_raw_filter_frequency.value = int(
            125e6 / (2**decimation) / 2
        )

        self.control.exposed_write_registers()
        # take care that new decimation was actually written to FPGA
        sleep(0.1)
        self.control.continue_acquisition()

    def exposed_stop(self):
        self.cleanup()


class PIDOptimization:
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.engine = MultiDimensionalOptimizationEngine(
            [[100, 4000], [100, 4000]], x0=[2000, 2000]
        )

    def run(self):
        try:
            self.parameters.psd_data_complete.on_change(
                self.psd_data_received, call_listener_with_first_value=False
            )
            self.parameters.psd_optimization_running.value = True
            self.start_single_psd_measurement()
        except:
            self.cleanup()
            raise

    def start_single_psd_measurement(self):
        new_params = self.engine.ask()
        self.parameters.p.value = int(new_params[0])
        self.parameters.i.value = int(new_params[1])

        self.psd_acquisition = PSDAcquisition(
            self.control, self.parameters, is_child=True
        )
        self.psd_acquisition.run()

    def cleanup(self):
        self.parameters.psd_optimization_running.value = False
        self.parameters.psd_data_complete.remove_listener(self.psd_data_received)

    def psd_data_received(self, psd_data_pickled):
        try:
            # psd data doesn't have to be stored here as a client that is interested
            # in it may listen to parameters.psd_data change events
            psd_data = pickle.loads(psd_data_pickled)

            params = (psd_data["p"], psd_data["i"])
            print("received fitness", psd_data["fitness"], params)

            self.engine.tell(psd_data["fitness"], params)

            self.start_single_psd_measurement()

            done = self.engine.finished()
            if done:
                # FIXME: implement use of optimized pid parameters
                self.cleanup()

        except:
            self.cleanup()
            raise

    def exposed_stop(self):
        self.cleanup()
