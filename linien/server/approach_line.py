import numpy as np
from time import sleep, time
from linien.common import determine_shift_by_correlation

ZOOM_STEP = 2


class Approacher:
    def __init__(self, control, parameters, first_error_signal, target_zoom):
        self.control = control
        self.parameters = parameters
        self.first_error_signal = first_error_signal
        self.target_zoom = target_zoom

        self.reset_properties()

    def reset_properties(self):
        self.history = []
        self.zoom_factor = 1
        self.N_at_this_zoom = 0
        self.last_shifts_at_this_zoom = None
        self.time_last_current_correction = None
        self.time_last_zoom = time()

    def approach_line(self, error_signal):
        if time() - self.time_last_zoom > 15:
            raise Exception('approaching took too long')

        initial_ramp_amplitude = self.parameters.autolock_initial_ramp_amplitude.value

        shift, zoomed_ref, zoomed_err = determine_shift_by_correlation(
            self.zoom_factor, self.first_error_signal, error_signal
        )
        shift *= initial_ramp_amplitude
        self.history.append((zoomed_ref, zoomed_err))
        self.history.append('shift %f' % (-1 * shift))

        if self.N_at_this_zoom == 0:
            # if we are at the final zoom, we should be very quick.
            # Therefore, we just correct the current and turn the lock on
            # immediately. We skip the rest of this method (drift detection etc.)
            next_step_is_lock = self.zoom_factor >= self.target_zoom
            if next_step_is_lock:
                return True
            else:
                self._correct_current(shift, allow_ramp_amplitude_decrease=True)
        else:
            # wait for some time after the last current correction
            if time() - self.time_last_current_correction < 1:
                return

            # check that the drift is slow
            # this is needed for systems that only react slowly to changes in
            # input parameters. In this case, we have to wait until the reaction
            # to the last input is done.
            shift_diff = np.abs(shift - self.last_shifts_at_this_zoom[-1])
            drift_slow = shift_diff < initial_ramp_amplitude / self.target_zoom / 8

            # if data comes in very slowly (<1 Hz), we skip the drift analysis
            # because it would take too much time
            low_recording_rate = self.parameters.ramp_speed.value > 10

            if low_recording_rate or drift_slow:
                is_close_to_target = shift < self.parameters.ramp_amplitude.value / 8
                if is_close_to_target:
                    return self._decrease_scan_range()
                else:
                    self._correct_current(shift)

        self.N_at_this_zoom += 1
        self.last_shifts_at_this_zoom = self.last_shifts_at_this_zoom or []
        self.last_shifts_at_this_zoom.append(shift)

    def _decrease_scan_range(self):
        self.N_at_this_zoom = 0
        self.last_shifts_at_this_zoom = None

        self.zoom_factor *= ZOOM_STEP
        self.time_last_zoom = time()

        self.control.pause_acquisition()

        self.parameters.ramp_amplitude.value /= ZOOM_STEP
        new_ramp_speed = self.parameters.ramp_speed.value - 1 \
            if self.parameters.ramp_speed.value > 5 \
            else self.parameters.ramp_speed.value
        self.parameters.ramp_speed.value = new_ramp_speed
        self.control.exposed_write_data()
        self.control.continue_acquisition()

    def _correct_current(self, shift, allow_ramp_amplitude_decrease=False):
        self.control.pause_acquisition()
        self.time_last_current_correction = time()

        self.parameters.center.value -= shift

        did_zoom = False
        if allow_ramp_amplitude_decrease:
            # we check whether at this shift the ramp goes beyond the maximum
            # because this is something we want to avoid
            # in this case, we decrease the ramp amplitude
            center = self.parameters.center.value
            amplitude = self.parameters.ramp_amplitude.value
            max_allowed_amplitude = 1 - abs(center)
            if amplitude > max_allowed_amplitude:
                self.parameters.ramp_amplitude.value = max_allowed_amplitude
                self.zoom_factor *= amplitude / max_allowed_amplitude
                did_zoom = True

        self.control.exposed_write_data()
        self.control.continue_acquisition()

        return did_zoom