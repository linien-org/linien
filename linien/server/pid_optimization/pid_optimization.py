import pickle
from scipy import signal
from time import time


# TODO: not all decimations are needed, steps > 1 can be made
DECIMATIONS = list(range(16))

# TODO: FÜR PSD TATSÄCHLICH BAYES VERWENDEN, WEIL LÄNGER DAUERT?


def residual_freq_noise(dt, sig):
    fs = 1 / dt
    num_pts = int(len(sig) / 128)
    hann = signal.hann(num_pts)
    f, psd = signal.welch(sig, fs=fs, window=hann, nperseg=num_pts)
    return f, psd


def psds_to_fitness(psds_by_decimation):
    fitness = 0

    for decimation, psd_data in psds_by_decimation.items():
        f, psd = psd_data
        fitness += sum(psd)

    return fitness


class PSDAcquisition:
    def __init__(self, control, parameters, decimations=DECIMATIONS):
        self.decimations = decimations
        self.decimation_index = 0

        self.recorded_signals_by_decimation = {}
        self.recorded_psds_by_decimation = {}

        self.running = True
        self.parameters = parameters
        self.control = control

    def run(self):
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

        if self.decimation_index < len(DECIMATIONS):
            new_decimation = DECIMATIONS[self.decimation_index]
            print("set new decimation", new_decimation)
            self.set_decimation(new_decimation)
        else:
            self.remove_listeners()
            self.running = False
            self.parameters.psd_data.value = pickle.dumps(
                {
                    "time": time(),
                    "p": self.parameters.p.value,
                    "i": self.parameters.i.value,
                    "d": self.parameters.d.value,
                    "signals": self.recorded_signals_by_decimation,
                    "psds": self.recorded_psds_by_decimation,
                    "fitness": psds_to_fitness(self.recorded_psds_by_decimation),
                }
            )

            self.control.pause_acquisition()
            self.parameters.acquisition_raw_enabled.value = False
            self.control.exposed_write_data()
            self.control.continue_acquisition()

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

    def run(self):
        self.psd_acquisition = PSDAcquisition(
            self.control,
            self.parameters,
        )
        self.psd_acquisition.run()

        self.parameters.psd_data.on_change(
            self.psd_data_received, call_listener_with_first_value=False
        )

    def remove_listeners(self):
        # TODO: if something fails, (try to) remove listeners
        self.parameters.psd_data.remove_listener(self.psd_data_received)

    def psd_data_received(self, psd_data):
        # TODO: calculate fitness
        # psd data doesn't have to be stored here as a client that is interested
        # in it may listen to parameters.psd_data change events

        done = True
        if done:
            self.remove_listeners()