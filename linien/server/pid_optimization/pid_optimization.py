import pickle
import random
import string
import numpy as np
from time import time
from scipy import signal

from linien.server.optimization.engine import MultiDimensionalOptimizationEngine

ALL_DECIMATIONS = list(range(32))


def residual_freq_noise(dt, sig):
    fs = 1 / dt
    # num_pts = int(len(sig) / 128)
    num_pts = 256
    hann = signal.hann(num_pts)

    f, psd = signal.welch(sig, fs=fs, window=hann, nperseg=num_pts, scaling="density")

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
            self.control.exposed_write_data()
            self.control.continue_acquisition()

    def react_to_new_signal(self, data_pickled):
        # FIXME: erster Datenpunkt oder letzter haben manchmal glitches --> entfernen?
        try:
            if not self.running or self.parameters.pause_acquisition.value:
                return

            data = pickle.loads(data_pickled)

            current_decimation = self.parameters.acquisition_raw_decimation.value
            print("recorded signal for decimation", current_decimation)
            print("recording took", time() - self.time_decimation_set, "s")
            self.recorded_signals_by_decimation[current_decimation] = data
            self.recorded_psds_by_decimation[current_decimation] = residual_freq_noise(
                1 / (125e6) * (2 ** (current_decimation)), data[0]
            )

            # note: we don't precalculate the decimation values because we
            # want the user to be able to change these values while the acquisition
            # is running (i.e. if the user notices that it takes too long)
            self.decimation_index += (
                self.parameters.psd_acquisition_decimation_step.value
            )

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
        self.control.exposed_write_data()
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
