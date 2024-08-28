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

import logging
import pickle
from typing import Union

import numpy as np
from linien_common.common import determine_shift_by_correlation, get_lock_point
from linien_common.communication import LinienControlService

from ..parameters import Parameters
from .approacher import Approacher
from .engine import OptimizerEngine
from .utils import FINAL_ZOOM_FACTOR

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SpectroscopyOptimizer:
    def __init__(self, control: LinienControlService, parameters: Parameters) -> None:
        self.control = control
        self.parameters = parameters

        self.initial_spectrum: Union[bytes, None] = None
        self.iteration: int = 0
        self.recenter_after: int = 2
        self.next_recentering_iteration: int = self.recenter_after
        self.allow_increase_of_recentering_interval: bool = True

        self.initial_sweep_speed = self.parameters.sweep_speed.value
        self.initial_sweep_amplitude = self.parameters.sweep_amplitude.value
        self.initial_sweep_center = self.parameters.sweep_center.value

    def run(self, x0: int, x1: int, spectrum: bytes) -> None:
        error_signal = pickle.loads(spectrum)

        self.parameters.optimization_failed.value = False
        self.parameters.optimization_approaching.value = True

        # record first
        cropped = error_signal[x0:x1]
        x0, x1 = x0 + int(np.argmin(cropped)), x0 + int(np.argmax(cropped))
        (mean_signal, _, target_zoom, first_error_signal, _, _) = get_lock_point(
            error_signal, *list(sorted([x0, x1])), final_zoom_factor=FINAL_ZOOM_FACTOR
        )

        self.approacher = Approacher(
            self.control, self.parameters, first_error_signal, target_zoom, mean_signal
        )
        self.engine = OptimizerEngine(self.control, self.parameters)
        self.parameters.to_plot.add_callback(
            self.react_to_new_spectrum, call_immediately=True
        )
        self.parameters.optimization_running.value = True
        self.parameters.optimization_improvement.value = 0

    def react_to_new_spectrum(self, spectrum: bytes) -> None:
        if self.parameters.optimization_running.value:
            try:
                dual_channel = self.parameters.dual_channel.value
                channel = self.parameters.optimization_channel.value
                spectrum_idx = 1 if not dual_channel else (1, 2)[channel]
                unpickled = pickle.loads(spectrum)
                spectrum = unpickled[f"error_signal_{spectrum_idx}"]
                quadrature = unpickled[f"error_signal_{spectrum_idx}_quadrature"]

                if self.parameters.optimization_approaching.value:
                    if self.approacher.approach_line(spectrum):  # approaching finished
                        logger.info("Approaching desired line finished.")
                        self.parameters.optimization_approaching.value = False
                else:  # continue with approach
                    self.iteration += 1
                    if self.initial_spectrum is None:
                        self.initial_spectrum = spectrum
                        self.engine.tell(spectrum, quadrature)
                    do_center_line = self.iteration == self.next_recentering_iteration
                    center_line_next_time = (
                        self.iteration + 1 == self.next_recentering_iteration
                    )
                    if self.iteration > 1:
                        if do_center_line:
                            # center the line again
                            shift, _, _ = determine_shift_by_correlation(
                                1, self.initial_spectrum, spectrum
                            )
                            self.parameters.sweep_center.value -= (
                                shift * self.parameters.sweep_amplitude.value
                            )
                            self.control.exposed_write_registers()
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
                        self.stop(True)  # we are done!
            except Exception:
                logger.exception("Exception at optimization task")
                self.parameters.optimization_failed.value = True
                self.stop(False)

    def stop(self, use_new_parameters: bool) -> None:
        if use_new_parameters and self.parameters.optimization_improvement.value > 0:
            self.engine.use_best_parameters()
        else:
            self.engine.request_and_set_new_parameters(use_initial_parameters=True)
        self.parameters.optimization_running.value = False
        self.parameters.to_plot.remove_callback(self.react_to_new_spectrum)
        self.parameters.task.value = None
        self.reset_sweep()

    def reset_sweep(self) -> None:
        self.control.exposed_pause_acquisition()
        self.parameters.sweep_amplitude.value = self.initial_sweep_amplitude
        self.parameters.sweep_center.value = self.initial_sweep_center
        self.control.exposed_write_registers()
        self.control.exposed_continue_acquisition()
