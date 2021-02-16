from linien.server.optimization.utils import FINAL_ZOOM_FACTOR
from linien.server.optimization.engine import OptimizerEngine
import pickle
import numpy as np
import traceback

from linien.common import determine_shift_by_correlation, get_lock_point
from linien.server.approach_line import Approacher


class OptimizeSpectroscopy:
    def __init__(self, control, parameters):
        self.control = control
        self.parameters = parameters

        self.initial_spectrum = None
        self.iteration = 0

        self.approacher = None

        self.recenter_after = 2
        self.next_recentering_iteration = self.recenter_after
        self.allow_increase_of_recentering_interval = True

        self.initial_ramp_speed = self.parameters.ramp_speed.value
        self.initial_ramp_amplitude = self.parameters.ramp_amplitude.value
        self.initial_ramp_center = self.parameters.center.value

    def run(self, x0, x1, spectrum):
        self.parameters.optimization_failed.value = False
        self.parameters.optimization_approaching.value = True

        spectrum = pickle.loads(spectrum)
        cropped = spectrum[x0:x1]
        min_idx = np.argmin(cropped)
        max_idx = np.argmax(cropped)
        self.x0, self.x1 = x0 + min_idx, x0 + max_idx

        self.record_first_error_signal(spectrum)

        params = self.parameters
        self.engine = OptimizerEngine(self.control, params)
        params.to_plot.on_change(self.react_to_new_spectrum)
        params.optimization_running.value = True
        params.optimization_improvement.value = 0

    def record_first_error_signal(self, error_signal):
        (
            mean_signal,
            _2,
            target_zoom,
            rolled_error_signal,
            line_width,
            peak_idxs,
        ) = get_lock_point(
            error_signal,
            *list(sorted([self.x0, self.x1])),
            final_zoom_factor=FINAL_ZOOM_FACTOR
        )

        self.target_zoom = target_zoom
        self.first_error_signal = rolled_error_signal

        self.approacher = Approacher(
            self.control,
            self.parameters,
            self.first_error_signal,
            self.target_zoom,
            mean_signal,
            allow_ramp_speed_change=False,
        )

    def react_to_new_spectrum(self, spectrum):
        if not self.parameters.optimization_running.value:
            return

        try:
            params = self.parameters

            dual_channel = params.dual_channel.value
            channel = params.optimization_channel.value
            spectrum_idx = 1 if not dual_channel else (1, 2)[channel]
            unpickled = pickle.loads(spectrum)
            spectrum = unpickled["error_signal_%d" % spectrum_idx]
            quadrature = unpickled["error_signal_%d_quadrature" % spectrum_idx]

            if self.parameters.optimization_approaching.value:
                approaching_finished = self.approacher.approach_line(spectrum)
                if approaching_finished:
                    self.parameters.optimization_approaching.value = False
            else:
                self.iteration += 1

                if self.initial_spectrum is None:
                    params = self.parameters
                    self.initial_spectrum = spectrum

                    self.engine.tell(spectrum, quadrature)

                center_line = self.iteration == self.next_recentering_iteration
                center_line_next_time = (
                    self.iteration + 1 == self.next_recentering_iteration
                )

                if self.iteration > 1:
                    if center_line:
                        # center the line again
                        shift, _, _2 = determine_shift_by_correlation(
                            1, self.initial_spectrum, spectrum
                        )
                        params.center.value -= shift * params.ramp_amplitude.value
                        self.control.exposed_write_data()

                        if (
                            self.allow_increase_of_recentering_interval
                            and abs(shift) < 2 / FINAL_ZOOM_FACTOR
                        ):
                            self.recenter_after *= 2
                        else:
                            self.allow_increase_of_recentering_interval = False

                        self.next_recentering_iteration += self.recenter_after
                    else:
                        self.engine.tell(spectrum, quadrature)

                if not self.engine.finished():
                    self.engine.request_and_set_new_parameters(
                        use_initial_parameters=center_line_next_time
                    )
                else:
                    # we are done!
                    self.exposed_stop(True)

        except:
            print("exception at optimization task")
            traceback.print_exc()
            self.parameters.optimization_failed.value = True
            self.exposed_stop(False)

    def exposed_stop(self, use_new_parameters):
        if use_new_parameters and self.parameters.optimization_improvement.value > 0:
            self.engine.use_best_parameters()
        else:
            self.engine.request_and_set_new_parameters(use_initial_parameters=True)

        self.parameters.optimization_running.value = False
        self.parameters.to_plot.remove_listener(self.react_to_new_spectrum)
        self.parameters.task.value = None

        self.reset_scan()

    def reset_scan(self):
        self.control.pause_acquisition()

        self.parameters.ramp_speed.value = self.initial_ramp_speed
        self.parameters.ramp_amplitude.value = self.initial_ramp_amplitude
        self.parameters.center.value = self.initial_ramp_center
        self.control.exposed_write_data()

        self.control.continue_acquisition()
