from linien.server.optimization.engine import MultiDimensionalOptimizationEngine
import pickle
import random
import string
from scipy import signal
from time import time


# TODO: not all decimations are needed, steps > 1 can be made
DECIMATIONS = list(range(17))
DECIMATIONS = [0, 4, 8, 12, 16]

# TODO: FÜR PSD TATSÄCHLICH BAYES VERWENDEN, WEIL LÄNGER DAUERT?


def residual_freq_noise(dt, sig):
    fs = 1 / dt
    # num_pts = int(len(sig) / 128)
    num_pts = 256
    hann = signal.hann(num_pts)
    f, psd = signal.welch(sig, fs=fs, window=hann, nperseg=num_pts)
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
    def __init__(self, control, parameters, decimations=DECIMATIONS, is_child=False):
        self.decimations = decimations
        self.decimation_index = 0

        self.recorded_signals_by_decimation = {}
        self.recorded_psds_by_decimation = {}

        self.running = True
        self.parameters = parameters
        self.control = control

        self.is_child = is_child

    def run(self):
        self.uuid = generate_curve_uuid()
        self.set_decimation(DECIMATIONS[0])
        self.add_listeners()

    def add_listeners(self):
        self.parameters.acquisition_raw_data.on_change(
            self.react_to_new_signal, call_listener_with_first_value=False
        )

    def remove_listeners(self):
        # TODO: if something fails, (try to) remove listeners
        self.parameters.acquisition_raw_data.remove_listener(self.react_to_new_signal)

    def react_to_new_signal(self, data_pickled):
        # FIXME: erster Datenpunkt oder letzter haben manchmal glitches --> entfernen?
        if not self.running or self.parameters.pause_acquisition.value:
            return

        data = pickle.loads(data_pickled)

        current_decimation = self.parameters.acquisition_raw_decimation.value
        print("recorded signal for decimation", current_decimation)
        self.recorded_signals_by_decimation[current_decimation] = data
        self.recorded_psds_by_decimation[current_decimation] = residual_freq_noise(
            1 / (125e6) * (2 ** (current_decimation)), data[0]
        )
        self.decimation_index += 1
        complete = self.decimation_index >= len(DECIMATIONS)
        self.publish_psd_data(complete)

        if not complete:
            new_decimation = DECIMATIONS[self.decimation_index]
            print("set new decimation", new_decimation)
            self.set_decimation(new_decimation)
        else:
            self.remove_listeners()
            self.running = False

            if not self.is_child:
                self.control.pause_acquisition()
                self.parameters.acquisition_raw_enabled.value = False
                self.control.exposed_write_data()
                self.control.continue_acquisition()

    def publish_psd_data(self, complete):
        self.parameters.psd_data.value = pickle.dumps(
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

    def set_decimation(self, decimation):
        self.control.pause_acquisition()
        self.parameters.acquisition_raw_decimation.value = decimation
        self.parameters.acquisition_raw_enabled.value = True
        self.control.exposed_write_data()
        self.control.continue_acquisition()


class PIDOptimization:
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.engine = MultiDimensionalOptimizationEngine([[100, 4000], [100, 4000]])

    def run(self):
        self.parameters.psd_data.on_change(
            self.psd_data_received, call_listener_with_first_value=False
        )
        self.start_single_psd_measurement()

    def start_single_psd_measurement(self):
        new_params = self.engine.ask()
        # FIXME: how to tell CMAES that only int is allowed?
        # FIXME: current parameters as x0
        # FIXME: CMAES renormalize checken
        self.parameters.p.value = int(new_params[0])
        self.parameters.i.value = int(new_params[1])

        self.psd_acquisition = PSDAcquisition(
            self.control, self.parameters, is_child=True
        )
        self.psd_acquisition.run()

    def remove_listeners(self):
        # TODO: if something fails, (try to) remove listeners
        self.parameters.psd_data.remove_listener(self.psd_data_received)

    def psd_data_received(self, psd_data_pickled):
        # TODO: calculate fitness
        # psd data doesn't have to be stored here as a client that is interested
        # in it may listen to parameters.psd_data change events
        psd_data = pickle.loads(psd_data_pickled)
        if not psd_data["complete"]:
            return

        params = (psd_data["p"], psd_data["i"])
        print("received fitness", psd_data["fitness"], params)

        self.engine.tell(psd_data["fitness"], params)

        # self.start_single_psd_measurement()

        done = True
        if done:
            # FIXME: implement
            self.remove_listeners()