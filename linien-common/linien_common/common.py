# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
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


"""This file contains stuff that is required by the server as well as the client."""

from enum import Enum, IntEnum
from time import time
from typing import Dict, List, Tuple, Union

import numpy as np
from scipy.signal import correlate, resample

MHz = 0x10000000 / 8
Vpp = ((1 << 14) - 1) / 4
# conversion of bits to V
ANALOG_OUT_V = 1.8 / ((2**15) - 1)

AUTOLOCK_MAX_N_INSTRUCTIONS = 32

DECIMATION = 8
MAX_N_POINTS = 16384
N_POINTS = int(MAX_N_POINTS / DECIMATION)


class FilterType(IntEnum):
    LOW_PASS = 0
    HIGH_PASS = 1


class OutputChannel(IntEnum):
    FAST_OUT1 = 0
    FAST_OUT2 = 1
    ANALOG_OUT0 = 2


class AutolockMode(IntEnum):
    AUTO_DETECT = 0
    ROBUST = 1
    SIMPLE = 2


class PSDAlgorithm(str, Enum):
    WELCH = "welch"
    LPSD = "lpsd"


class SpectrumUncorrelatedException(Exception):
    pass


def downsample_history(
    times: list, values: list, max_time_diff: float, max_N: int = N_POINTS
) -> None:
    """
    The history should not grow too much. When recording for long intervals, we want to
    throw away some datapoints that were recorded with a sampling rate that is too high.
    This function takes care of this.
    """
    last_time = None

    to_remove = []

    for idx in range(len(times)):
        current_time = times[idx]
        remove = False

        if last_time is not None:
            if np.abs(last_time - current_time) < max_time_diff / max_N:
                remove = True

        if remove:
            to_remove.append(idx)
        else:
            last_time = current_time

    for idx in reversed(to_remove):
        times.pop(idx)
        values.pop(idx)


def truncate(times, values, max_time_diff):
    while len(values) > 0:
        if time() - times[0] > max_time_diff:
            times.pop(0)
            values.pop(0)
            continue
        break


def update_signal_history(
    control_history: Dict[str, List[float]],
    monitor_history: Dict[str, List[float]],
    to_plot,
    is_locked: bool,
    max_time_diff: float,
) -> Union[
    Tuple[Dict[str, List[float]], Dict[str, List[float]]], Dict[str, List[float]]
]:
    if not to_plot:
        return control_history

    if is_locked:
        control_history["values"].append(np.mean(to_plot["control_signal"]))
        control_history["times"].append(time())

        if "slow_control_signal" in to_plot:
            control_history["slow_values"].append(to_plot["slow_control_signal"])
            control_history["slow_times"].append(time())

        if "monitor_signal" in to_plot:
            monitor_history["values"].append(np.mean(to_plot["monitor_signal"]))
            monitor_history["times"].append(time())

    else:
        control_history["values"] = []
        control_history["times"] = []
        control_history["slow_values"] = []
        control_history["slow_times"] = []
        monitor_history["values"] = []
        monitor_history["times"] = []

    # truncate
    truncate(control_history["times"], control_history["values"], max_time_diff)
    truncate(
        control_history["slow_times"], control_history["slow_values"], max_time_diff
    )
    truncate(monitor_history["times"], monitor_history["values"], max_time_diff)

    # downsample
    downsample_history(
        control_history["times"], control_history["values"], max_time_diff
    )
    downsample_history(
        control_history["slow_times"], control_history["slow_values"], max_time_diff
    )
    downsample_history(
        monitor_history["times"], monitor_history["values"], max_time_diff
    )
    return control_history, monitor_history


def check_whether_correlation_is_bad(correlation, N):
    return np.max(correlation) < 0.1


def determine_shift_by_correlation(zoom_factor, reference_signal, error_signal):
    """
    Compare two spectra and determines the shift by correlation.

    `zoom_factor` is the zoom factor of `error_signal` with respect to
    `reference_signal`, i.e. it states how much reference signal has to be magnified in
    order to show the same region as the new error signal.
    """
    # values that should not be considered are np.nan but the correlation has problems
    # with np.nans --> we set it to 0
    reference_signal[np.isnan(reference_signal)] = 0
    error_signal[np.isnan(error_signal)] = 0

    # prepare the signals in order to get a normalized cross-correlation
    # this is required in order for `check_whether_correlation_is_bad` to return
    # senseful answer
    # cf. https://stackoverflow.com/questions/53436231/normalized-cross-correlation-in-python  # noqa: E501
    reference_signal = (reference_signal - np.mean(reference_signal)) / (
        np.std(reference_signal) * len(reference_signal)
    )
    error_signal = (error_signal - np.mean(error_signal)) / (np.std(error_signal))

    length = len(error_signal)
    center_idx = int(length / 2)

    # crop the reference signal such that it shows the same region as the new
    # error signal
    idx_shift = int(length * (1 / zoom_factor / 2))
    zoomed_ref = reference_signal[center_idx - idx_shift : center_idx + idx_shift]

    # correlation is slow on red pitaya --> use at maximum 4096 points
    skip_factor = int(len(zoomed_ref) / 4096)
    if skip_factor < 1:
        skip_factor = 1
    zoomed_ref = zoomed_ref[::skip_factor]

    # now sample the error signal down to the same length as the zoomed
    # reference signal
    downsampled_error_signal = resample(error_signal, len(zoomed_ref))

    correlation = correlate(zoomed_ref, downsampled_error_signal)

    if check_whether_correlation_is_bad(correlation, len(zoomed_ref)):
        raise SpectrumUncorrelatedException()

    shift = np.argmax(correlation)
    shift = (shift - len(zoomed_ref)) / len(zoomed_ref) * 2 / zoom_factor

    return shift, zoomed_ref, downsampled_error_signal


def get_lock_point(
    error_signal: np.ndarray, x0: int, x1: int, final_zoom_factor: float = 1.5
) -> Tuple[float, bool, float, np.ndarray, int, Tuple[int, int]]:
    """Calculate parameters for the autolock based on the initial error signal.

    Takes the `error_signal` and two points (`x0` and `x1`) as arguments. The points are
    the points selected by the user, and we know that we want to lock between them.

    Use `final_zoom_factor` to specify how wide the line should be in the end:
    - 1: in the end, only the line should be visible
    - 5: an area of 5 times the linewidth should be visible
    """
    length = len(error_signal)

    # the data that is between the user-selected bounds
    cropped_data = np.array(error_signal[x0:x1])

    min_idx = np.argmin(cropped_data)
    max_idx = np.argmax(cropped_data)
    line_width = abs(max_idx - min_idx)

    # the y value that is between minimum and maximum
    mean_signal = np.mean([cropped_data[min_idx], cropped_data[max_idx]])
    idxs = sorted([min_idx, max_idx])
    slope_data = np.array(cropped_data[idxs[0] : idxs[1]]) - mean_signal

    peak_idxs = (int(idxs[0] + x0), int(idxs[1] + x0))

    zero_idx = x0 + np.min(idxs) + np.argmin(np.abs(slope_data))

    # roll the error signal such that the target lock point is exactly in the
    # center
    roll = -int(zero_idx - (length / 2))

    # set all the rolled points to nan such that they don't contribute
    # in the correlation
    filler = np.empty(abs(roll))
    filler[:] = np.nan

    if roll < 0:
        rolled_error_signal = np.hstack((error_signal[-roll:], filler))
    else:
        rolled_error_signal = np.hstack((filler, error_signal[:-roll]))

    target_slope_rising = max_idx > min_idx
    target_zoom = N_POINTS / (idxs[1] - idxs[0]) / final_zoom_factor

    return (
        float(mean_signal),
        bool(target_slope_rising),
        float(target_zoom),
        np.array(rolled_error_signal),
        int(line_width),
        peak_idxs,
    )


def convert_channel_mixing_value(value: int) -> Tuple[int, int]:
    if value <= 0:
        a_value = 128
        b_value = 128 + value
    else:
        a_value = 127 - value
        b_value = 128

    return a_value, b_value


def combine_error_signal(
    error_signals, dual_channel, channel_mixing, combined_offset, chain_factor_width=8
):
    if not dual_channel:
        signal = error_signals[0]
    else:
        a_factor, b_factor = convert_channel_mixing_value(channel_mixing)

        signal = [
            (a_factor * a + b_factor * b) >> chain_factor_width
            for a, b in zip(*error_signals)
        ]

    return np.array([v + combined_offset for v in signal])


def check_plot_data(is_locked: bool, plot_data) -> bool:
    if is_locked:
        if "error_signal" not in plot_data or "control_signal" not in plot_data:
            return False
    else:
        if "error_signal_1" not in plot_data:
            return False
    return True


def get_signal_strength_from_i_q(i, q):
    i = i.astype(np.int64)
    q = q.astype(np.int64)
    i_squared = i**2
    q_squared = q**2
    signal_strength = np.sqrt(i_squared + q_squared)
    return signal_strength
