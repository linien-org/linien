# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
# Copyright 2023 Christian Freier <christian.freier@nomadatomics.com>
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

import json
import logging
from time import time
from typing import Any, Callable, Iterator

import linien_server
from linien_common.common import AutolockMode, MHz, PSDAlgorithm, Vpp
from linien_common.config import USER_DATA_PATH

PARAMETER_STORE_FILENAME = "parameters.json"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Parameter:
    """Represents a single parameter and is used by `Parameters`."""

    def __init__(
        self,
        min_=None,
        max_=None,
        start=None,
        wrap=False,
        sync=True,
        collapsed_sync=True,
        restorable=False,
        loggable=False,
        log=False,
    ):
        self.min = min_
        self.max = max_
        self.wrap = wrap
        self._value = start
        self._start = start
        self._callbacks = set()
        self.can_be_cached = sync
        self._collapsed_sync = collapsed_sync
        self.restorable = restorable
        self.loggable = loggable
        self.log = log

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        # check bounds
        if self.min is not None and value < self.min:
            value = self.min if not self.wrap else self.max
        if self.max is not None and value > self.max:
            value = self.max if not self.wrap else self.min

        self._value = value

        # We copy it because a listener could remove a listener --> this would cause an
        # error in this loop.
        for callback in self._callbacks.copy():
            callback(value)

    def reset(self):
        self.value = self._start

    def add_callback(
        self, function: Callable[[Any], None], call_immediately: bool = False
    ) -> None:
        self._callbacks.add(function)

        if call_immediately:
            if self._value is not None:
                function(self._value)

    def remove_callback(self, function: Callable[[Any], None]) -> None:
        if function in self._callbacks:
            self._callbacks.remove(function)


class Parameters:
    """
    This class defines the parameters of the Linien server. They represent the public
    interface and can be used to control the behavior of the server.

    Access on the server takes place like this:

        # retrieve a parameter
        foo(parameters.modulation_amplitude.value)

        # set a parameter
        parameters.modulation_amplitude.value = 0.5 * Vpp

        # if a parameter influences the behavior of the FPGA, it has to be
        # written to the FPGA as well (`control` is an instance of
        # `RedPitayaControlService`):
        control.exposed_write_registers()

    On the client side, access happens through `RemoteParameters` which
    transparently mimics the behavior of this class. Have a look at the comments
    below for a description of each parameter.
    """

    def __init__(self):
        # dict[str, list[tuple[str, Any]]]
        self._changed_parameters_queue = {}
        # dict[tuple[Parameter, Callable[[Any], None]]]
        self._remote_listener_callbacks = {}

        self.to_plot = Parameter(sync=False)
        """
        The `to_plot` parameter is a pickled dictionary that contains signals that may
        be plotted. Depending on the locking state, it may contain these signals:
        Unlocked state:
          - `error_signal_1` and `error_signal_1_quadrature`:
              IQ-demodulated and low-pass-filtered error signals from ANALOG IN 0
          - `error_signal_2` and `error_signal_2_quadrature`:
              IQ-demodulated and low-pass-filtered error signals from ANALOG IN 1. These
              signals are only available if in dual-channel spectroscopy mode is
              enabled. Otherwise the un-demodulated monitor_signal` is shown.
          - `monitor_signal`:
              Signal recorded from ANALOG IN 1 without demodulation. Only available if
              dual channel mode is not enabled.
        Locked state:
          - `error_signal`:
              Error signal that is fed into the PID controller.
          - `control_signal`:
              Output of the PID controller.
          - `slow`:
              Output of slow additional integrator on slow analog output. Note that this
              value is not an array but a single point.
        """

        self.signal_stats = Parameter(sync=False, loggable=True)
        """
        A dictionary that contains mean, standard deviation, minimum value and maximum
        value for all the signals contained in `to_plot`. Exemplary dictionary keys are
        `error_signal_mean`, `control_signal_std`, `monitor_signal_min` or
        `error_signal_2_max`.
        """

        # ------------------- GENERAL PARAMETERS ---------------------------------------

        self.mod_channel = Parameter(start=0, min_=0, max_=1, restorable=True)
        """
        Configures the output of the modulation frequency. A value of 0 means FAST OUT 1
        and a value of 1 corresponds to FAST OUT 2
        """

        self.sweep_channel = Parameter(start=1, min_=0, max_=2, restorable=True)
        """
        Configures the output of the scan sweep:
            0 --> FAST OUT 1
            1 --> FAST OUT 2
            2 --> ANALOG OUT 0 (slow channel)
        """

        self.control_channel = Parameter(start=1, min_=0, max_=1, restorable=True)
        """
        Configures the output of the lock signal. A value of 0 means FAST OUT 1 and a
        value of 1 corresponds to FAST OUT 2
        """

        self.slow_control_channel = Parameter(start=2, min_=0, max_=2, restorable=True)
        """
        Configures the output of the slow PID control:
            0 --> FAST OUT 1
            1 --> FAST OUT 2
            2 --> ANALOG OUT 0 (slow channel)
        """

        self.gpio_p_out = Parameter(start=0, min_=0, max_=0b11111111)
        """
        set the output of GPIO pins. Each bit corresponds to one pin, i.e.
        `parameters.gpio_p_out.value = 0b11110000` turns on the first 4 pins and turns
        off the other ones.
        """
        self.gpio_n_out = Parameter(start=0, min_=0, max_=0b11111111)
        """
        set the output of GPIO pins. Each bit corresponds to one pin, i.e.
        `parameters.gpio_p_out.value = 0b11110000` turns on the first 4 pins and turns
        off the other ones.
        """

        # ANALOG_OUT0 is used for slow PID --> it can't be controlled manually
        self.analog_out_1 = Parameter(
            start=0, min_=0, max_=(2**15) - 1, restorable=True
        )
        """
        parameters for setting ANALOG_OUT 1 voltage.
        Usage: `parameters.analog_out_1.value = 1.2 * ANALOG_OUT_V`
        Minimum value is 0 and maximum 1.8 * ANALOG_OUT_V
        """
        self.analog_out_2 = Parameter(
            start=0, min_=0, max_=(2**15) - 1, restorable=True
        )
        """
        parameters for setting ANALOG_OUT 1 voltage.
        Usage: `parameters.analog_out_2.value = 1.2 * ANALOG_OUT_V`
        Minimum value is 0 and maximum 1.8 * ANALOG_OUT_V
        """
        self.analog_out_3 = Parameter(
            start=0, min_=0, max_=(2**15) - 1, restorable=True
        )
        """
        parameters for setting ANALOG_OUT 1 voltage.
        Usage: `parameters.analog_out_3.value = 1.2 * ANALOG_OUT_V`
        Minimum value is 0 and maximum 1.8 * ANALOG_OUT_V
        """

        self.lock = Parameter(start=False, loggable=True)
        """If `True`, this parameter turns off the sweep and starts the PID"""

        self.polarity_fast_out1 = Parameter(start=False, restorable=True)
        """
        Defines whether tuning the voltage up correspond to tuning the laser frequency
        up or down. Setting these values correctly is only required when using both, a
        fast out and a the slow output for PID
        """

        self.polarity_fast_out2 = Parameter(start=False, restorable=True)
        """
        Defines whether tuning the voltage up correspond to tuning the laser frequency
        up or down. Setting these values correctly is only required when using both, a
        fast out and a the slow output for PID
        """

        self.polarity_analog_out0 = Parameter(start=False, restorable=True)
        """
        Defines whether tuning the voltage up correspond to tuning the laser frequency
        up or down. Setting these values correctly is only required when using both, a
        fast out and a the slow output for PID
        """

        self.control_signal_history_length = Parameter(start=600)
        """Record of control signal should be kept for how long?"""

        self.control_signal_history = Parameter(
            start={"times": [], "values": []}, sync=False
        )

        self.monitor_signal_history = Parameter(
            start={"times": [], "values": []}, sync=False
        )

        self.pause_acquisition = Parameter(start=False)
        """
        If this boolean is `True`, no new spectroscopy data is sent to the clients. This
        parameter is used when writing data to FPGA that would result in cropped or
        distorted signals being displayed.
        """

        self.fetch_additional_signals = Parameter(start=True)
        """
        This parameter is not exposed to GUI. It is used by the autolock or normal lock
        to fetch less data if they are not needed.
        """

        self.ping = Parameter(start=0)
        """
        This is just a counter that is automatically increased every second. Its purpose
        is to allow for periodic tasks on the server: just register a callback with
         `add_callback` for this parameter.
        """

        # ------------------- SWEEP PARAMETERS -----------------------------------------

        self.sweep_amplitude = Parameter(min_=0.001, max_=1, start=1, loggable=True)
        """
        Amplitude of the sweep in units of 0.5 * Vpp of the output (2 V for fast outputs
        (range +/- 1 V) and 0.9 V for slow outputs (range 0 V to 1.8 V). That means an
        amplitude of 1.0 corresponds to the full sweep range in both cases.
        """

        self.sweep_center = Parameter(min_=-1, max_=1, start=0, loggable=True)
        """
        The center position of the sweep. If a fast output is used for the sweep this is
        the sweep center position in volts. If the slow output is used the interval
        [-1, +1] of this parameter is mapped to the interval [0V, +1.8V].
        """

        self.sweep_speed = Parameter(
            min_=0, max_=32, start=8, restorable=True, loggable=True
        )
        """
        The sweep speed in internal units. The actual speed is given by
        f_real = 3.8 kHz / (2 ** sweep_speed)
        Allowed values are [0, ..., 16]
        """

        self.sweep_pause = Parameter(start=False, loggable=True)
        """If set to `True`, this parameter pauses the sweep at the `sweep_center`."""

        # ------------------- MODULATION PARAMETERS ------------------------------------

        self.modulation_amplitude = Parameter(
            min_=0, max_=(1 << 14) - 1, start=1 * Vpp, restorable=True, loggable=True
        )
        """
        The amplitude of the modulation in internal units. Use Vpp for conversion to
        volts peak-peak, e.g: `parameters.modulation_amplitude.value = 0.5 * Vpp`
        Values between 0 and 2 * Vpp are allowed.
        """

        self.modulation_frequency = Parameter(
            min_=0, max_=0xFFFFFFFF, start=15 * MHz, restorable=True, loggable=True
        )
        """
        Frequency of the modulation in internal units. Use MHz for conversion to
        human-readable frequency, e.g:
            `parameters.modulation_frequency.value = 6.6 * MHz`
        By design, values up to 128 * MHz = 0xffffffff are allowed although in practice
        values of more than 50 MHz don't make sense due to the limited sampling rate of
        the DAC.
        """

        # ------------------- DEMODULATION AND FILTER PARAMETERS -----------------------
        self.pid_only_mode = Parameter(start=False, restorable=True)
        """
        PID-only mode allows to bypass demodulation, IIR filtering and offset.
        """

        self.dual_channel = Parameter(start=False, restorable=True)
        """
        Linien allows for two simultaneous demodulation channels. By default, only one
        is enabled. This is controlled by `dual_channel`.
        """

        self.channel_mixing = Parameter(start=0, restorable=True, loggable=True)
        """
        If in dual channel mode, what is the mixing ratio between them? A value of 0
        corresponds to equal ratio
                   -128             only channel A being active
                   128              only channel B being active
        Integer values [-128, ..., 128] are allowed.
        """

        # The following parameters exist twice, i.e. once per channel
        self.demodulation_phase_a = Parameter(
            min_=0, max_=360, start=0x0, wrap=True, restorable=True, loggable=True
        )
        """The demodulation phase for channel A in degree (0-360)"""

        self.demodulation_phase_b = Parameter(
            min_=0, max_=360, start=0x0, wrap=True, restorable=True, loggable=True
        )
        """The demodulation phase for channel B in degree (0-360)"""

        self.demodulation_multiplier_a = Parameter(
            min_=0, max_=15, start=1, restorable=True, loggable=True
        )
        """
        This parameter allows for multi-f (e.g. 3f or 5f) demodulation. Default value is
        1, indicating that 1f demodulation is used.
        """

        self.demodulation_multiplier_b = Parameter(
            min_=0, max_=15, start=1, restorable=True, loggable=True
        )
        """
        This parameter allows for multi-f (e.g. 3f or 5f) demodulation. Default value is
        1, indicating that 1f demodulation is used.
        """

        self.offset_a = Parameter(
            min_=-8191, max_=8191, start=0, restorable=True, loggable=True
        )
        """
        The vertical offset for channel A. A value of -8191 shifts the data down by 1V,
        a value of +8191 moves it up.
            """

        self.offset_b = Parameter(
            min_=-8191, max_=8191, start=0, restorable=True, loggable=True
        )
        """
        The vertical offset for channel B. A value of -8191 shifts the data down by 1V,
        a value of +8191 moves it up.
            """

        self.invert_a = Parameter(start=False, restorable=True)
        """A boolean indicating whether the channel A data should be inverted."""

        self.invert_b = Parameter(start=False, restorable=True)
        """A boolean indicating whether the channel B data should be inverted."""

        # -------   FILTER PARAMETERS   ------------------------------------------------
        self.filter_automatic_a = Parameter(start=True, restorable=True)
        """
        After demodulation of the signal, Linien may apply up to two IIR filters.
        `filter_automatic` is a boolean indicating whether Linien should automatically
        determine suitable filter for a given modulation frequency or whether the user
        may configure the filters himself. If automatic mode is enabled, two low pass
        filters are installed with a frequency of half the modulation frequency.
        """

        self.filter_automatic_b = Parameter(start=True, restorable=True)
        """
        After demodulation of the signal, Linien may apply up to two IIR filters.
        `filter_automatic` is a boolean indicating whether Linien should automatically
        determine suitable filter for a given modulation frequency or whether the user
        may configure the filters himself. If automatic mode is enabled, two low pass
        filters are installed with a frequency of half the modulation frequency.
        """

        self.filter_1_enabled_a = Parameter(start=False, restorable=True)
        """
        Should this filter be enabled? Note that disabling a filter does not bypass it
        as this would change the propagation time of the signal through the FPGA which
        is unfavorable as it leads to a mismatch of the demodulation phase. Instead, a
        filter with unity gain is installed.
        """

        self.filter_2_enabled_a = Parameter(start=False, restorable=True)
        """
        Should this filter be enabled? Note that disabling a filter does not bypass it
        as this would change the propagation time of the signal through the FPGA which
        is unfavorable as it leads to a mismatch of the demodulation phase. Instead, a
        filter with unity gain is installed.
        """

        self.filter_1_enabled_b = Parameter(start=False, restorable=True)
        """
        Should this filter be enabled? Note that disabling a filter does not bypass it
        as this would change the propagation time of the signal through the FPGA which
        is unfavorable as it leads to a mismatch of the demodulation phase. Instead, a
        filter with unity gain is installed.
        """

        self.filter_2_enabled_b = Parameter(start=False, restorable=True)
        """
        Should this filter be enabled? Note that disabling a filter does not bypass it
        as this would change the propagation time of the signal through the FPGA which
        is unfavorable as it leads to a mismatch of the demodulation phase. Instead, a
        filter with unity gain is installed.
        """

        self.filter_1_frequency_a = Parameter(start=10000, restorable=True)
        """The filter frequency in units of Hz"""

        self.filter_2_frequency_a = Parameter(start=10000, restorable=True)
        """The filter frequency in units of Hz"""

        self.filter_1_frequency_b = Parameter(start=10000, restorable=True)
        """The filter frequency in units of Hz"""

        self.filter_2_frequency_b = Parameter(start=10000, restorable=True)
        """The filter frequency in units of Hz"""

        self.filter_1_type_a = Parameter(start=0, restorable=True)
        """
        Either `LOW_PASS` or `HIGH_PASS` of linien_common.common.FilterType` enum class.
        """

        self.filter_2_type_a = Parameter(start=0, restorable=True)
        """
        Either `LOW_PASS` or `HIGH_PASS` of linien_common.common.FilterType` enum class.
        """

        self.filter_1_type_b = Parameter(start=0, restorable=True)
        """
        Either `LOW_PASS` or `HIGH_PASS` of linien_common.common.FilterType` enum class.
        """

        self.filter_2_type_b = Parameter(start=0, restorable=True)
        """
        Either `LOW_PASS` or `HIGH_PASS` of linien_common.common.FilterType` enum class.
        """

        # ------------------- LOCK AND PID PARAMETERS ----------------------------------

        self.combined_offset = Parameter(min_=-8191, max_=8191, start=0)
        """
        After combining channels A and B and before passing the result to the PID,
        `combined_offset` is added. It uses the same units as the channel offsets, i.e.
        a value of -8191 shifts the data down by 1V, a value of +8191 moves it up.
        """

        self.p = Parameter(start=50, max_=8191, restorable=True, loggable=True)
        """
        Proportional part of PID parameters. Range is [0, 8191]. In order to change sign
        of PID parameters, use `target_slope_rising`
        """

        self.i = Parameter(start=5, max_=8191, restorable=True, loggable=True)
        """
        Integral part of PID parameters. Range is [0, 8191]. In order to change sign of
        PID parameters, use `target_slope_rising`
        """

        self.d = Parameter(start=0, max_=8191, restorable=True, loggable=True)
        """
        Derivate part of PID parameters. Range is [0, 8191]. In order to change sign of
        PID parameters, use `target_slope_rising`
        """

        self.target_slope_rising = Parameter(start=True)
        """A boolean that inverts the sign of the PID parameters"""

        self.pid_on_slow_enabled = Parameter(start=False, restorable=True)
        """Whether the PID on ANALOG_OUT 0 is enabled."""

        self.pid_on_slow_strength = Parameter(start=0, restorable=True)
        """
        Strength of the slow PID. This strength corresponds to the strength of the
        integrator. Maximum value is 8191.
        """

        self.check_lock = Parameter(start=True, restorable=True)
        self.watch_lock = Parameter(start=True, restorable=True)
        self.watch_lock_threshold = Parameter(start=0.01, restorable=True)

        # ------------------- AUTOLOCK PARAMETERS --------------------------------------
        # These parameters are used internally by the optimization algorithm and usually
        # should not be manipulated
        self.task = Parameter(start=None, sync=False)
        self.automatic_mode = Parameter(start=True)
        self.autolock_target_position = Parameter(start=0)
        self.autolock_mode_preference = Parameter(
            start=AutolockMode.AUTO_DETECT, restorable=True
        )
        self.autolock_mode = Parameter(start=AutolockMode.SIMPLE)
        self.autolock_time_scale = Parameter(start=0)
        self.autolock_instructions = Parameter(start=[], sync=False)
        self.autolock_final_wait_time = Parameter(start=0)
        self.autolock_selection = Parameter(start=False)
        self.autolock_running = Parameter(start=False)
        self.autolock_preparing = Parameter(start=False)
        self.autolock_percentage = Parameter(start=0, min_=0, max_=100)
        self.autolock_watching = Parameter(start=False)
        self.autolock_failed = Parameter(start=False)
        self.autolock_locked = Parameter(start=False)
        self.autolock_retrying = Parameter(start=False)
        self.autolock_determine_offset = Parameter(start=True, restorable=True)
        self.autolock_initial_sweep_amplitude = Parameter(start=1)

        # ------------------- OPTIMIZATION PARAMETERS ----------------------------------
        # These parameters are used internally by the optimization algorithm and usually
        # should not be manipulated
        self.optimization_selection = Parameter(start=False)
        self.optimization_running = Parameter(start=False)
        self.optimization_approaching = Parameter(start=False)
        self.optimization_improvement = Parameter(start=0)
        self.optimization_mod_freq_enabled = Parameter(start=1)
        self.optimization_mod_freq_min = Parameter(start=0.0)
        self.optimization_mod_freq_max = Parameter(start=10.0)
        self.optimization_mod_amp_enabled = Parameter(start=1)
        self.optimization_mod_amp_min = Parameter(start=0.0)
        self.optimization_mod_amp_max = Parameter(start=2.0)
        self.optimization_optimized_parameters = Parameter(start=(0, 0, 0))
        self.optimization_channel = Parameter(start=0)
        self.optimization_failed = Parameter(start=False)

        # ------------------- PID OPTIMIZATION PARAMETERS ------------------------------
        # These parameters are used internally by the optimization algorithm and usually
        # should not be manipulated
        self.acquisition_raw_enabled = Parameter(start=False)
        self.acquisition_raw_decimation = Parameter(start=1)
        self.acquisition_raw_data = Parameter()
        self.acquisition_raw_filter_enabled = Parameter(start=False)
        """
        Raw acquisition has an additional iir filter that can be used as low pass for
        preventing alias effects
        """

        self.acquisition_raw_filter_frequency = Parameter(start=0)
        """The filter frequency in units of Hz"""

        self.psd_data_partial = Parameter(start=None)
        self.psd_data_complete = Parameter(start=None)
        self.psd_algorithm = Parameter(start=PSDAlgorithm.LPSD)
        self.psd_acquisition_running = Parameter(start=False)
        self.psd_optimization_running = Parameter(start=False)
        self.psd_acquisition_max_decimation = Parameter(
            start=18, min_=1, max_=32, restorable=True
        )

    def __iter__(self) -> Iterator[tuple[str, Parameter]]:
        for name, param in self.__dict__.items():
            if isinstance(param, Parameter):
                yield name, param

    def init_parameter_sync(
        self, uuid: str
    ) -> Iterator[tuple[str, Any, bool, bool, bool, bool]]:
        """
        To be called by a remote client: Yields all parameters as well as their values
        and if the parameters are suited to be cached registers a listener that pushes
        changes of these parameters to the client.
        """
        for name, param in self:
            yield (
                name,
                param.value,
                param.can_be_cached,
                param.restorable,
                param.loggable,
                param.log,
            )
            if param.can_be_cached:
                self.register_remote_listener(uuid, name)

    def register_remote_listener(self, uuid: str, param_name: str) -> None:
        self._changed_parameters_queue.setdefault(uuid, [])
        self._remote_listener_callbacks.setdefault(uuid, [])

        def append_changed_values_to_queue(value: Any) -> None:
            """Appends changed values to the queue of a specific client."""
            if uuid in self._changed_parameters_queue:
                self._changed_parameters_queue[uuid].append((param_name, value))

        param: Parameter = getattr(self, param_name)
        param.add_callback(append_changed_values_to_queue, call_immediately=True)

        self._remote_listener_callbacks[uuid].append(
            (param, append_changed_values_to_queue)
        )

    def unregister_remote_listeners(self, uuid: str):
        for param, callback in self._remote_listener_callbacks[uuid]:
            param.remove_callback(callback)

        del self._changed_parameters_queue[uuid]
        del self._remote_listener_callbacks[uuid]

    def get_changed_parameters_queue(self, uuid: str) -> list[tuple[str, Any]]:
        """Get the queue of parameter changes for a specific client."""
        queue = self._changed_parameters_queue.get(uuid, [])
        self._changed_parameters_queue[uuid] = []

        # filter out multiple values for collapsible parameters
        already_has_value = []
        for idx in reversed(range(len(queue))):
            param_name, value = queue[idx]
            if getattr(self, param_name)._collapsed_sync:
                if param_name in already_has_value:
                    del queue[idx]
                else:
                    already_has_value.append(param_name)
        return queue


def restore_parameters(parameters: Parameters) -> Parameters:
    """When the server starts, this method restores previously saved parameters."""
    filename = str(USER_DATA_PATH / PARAMETER_STORE_FILENAME)
    try:
        with open(filename, "r") as f:
            logger.info(f"Restoring parameters from {filename}")
            data = json.load(f)
    except FileNotFoundError:
        logger.info(f"Couldn't find {filename}. Using default parameters.")
        return parameters

    for name, attributes in data["parameters"].items():
        try:
            getattr(parameters, name).value = attributes["value"]
            getattr(parameters, name).log = attributes["log"]
        except AttributeError:  # ignore parameters that don't exist (anymore)
            continue
    logger.info(f"Restored parameters from {filename}")
    return parameters


def save_parameters(parameters: Parameters) -> None:
    """Gather all parameters and store them on disk."""

    parameters_dict = {}
    for name, param in parameters:
        if param.restorable:
            parameters_dict[name] = {"value": param.value, "log": param.log}

    filename = str(USER_DATA_PATH / PARAMETER_STORE_FILENAME)
    with open(filename, "w") as f:
        json.dump(
            {
                "version": linien_server.__version__,
                "time": time(),
                "parameters": parameters_dict,
            },
            f,
            indent=2,
        )
    logger.info(f"Saved parameters to {filename}")
