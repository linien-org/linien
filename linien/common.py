import numpy as np
from time import time
from scipy.signal import correlate, resample


LOW_PASS_FILTER = 0
HIGH_PASS_FILTER = 1


def downsample(times, values, max_time_diff, max_N=16384):
    last_time = None

    for idx in reversed(range(len(times))):
        current_time = times[idx]
        remove = False

        if last_time is not None:
            if np.abs(last_time - current_time) < max_time_diff / max_N:
                remove = True

        if remove:
            times.pop(idx)
            values.pop(idx)
        else:
            last_time = current_time


def truncate(times, values, max_time_diff):
    while len(values) > 0:
        if time() - times[0] > max_time_diff:
            times.pop(0)
            values.pop(0)
            continue
        break


def update_control_signal_history(history, to_plot, is_locked, max_time_diff):
    if not to_plot:
        return history

    now = time()

    if is_locked:
        history['values'].append(np.mean(to_plot['control_signal']))
        history['times'].append(time())

        if 'slow' in to_plot:
            history['slow_values'].append(to_plot['slow'])
            history['slow_times'].append(time())
    else:
        history['values'] = []
        history['times'] = []
        history['slow_values'] = []
        history['slow_times'] = []

    # truncate
    truncate(history['times'], history['values'], max_time_diff)
    truncate(history['slow_times'], history['slow_values'], max_time_diff)

    # downsample
    downsample(history['times'], history['values'], max_time_diff)
    downsample(history['slow_times'], history['slow_values'], max_time_diff)

    return history


def determine_shift_by_correlation(zoom_factor, reference_signal, error_signal):
    """Compares two spectra and determines the shift by correlation.

    `zoom_factor` is the zoom factor of `error_signal` with respect to
    `reference_signal`, i.e. it states how much reference signal has to be
    magnified in order to show the same region as the new error signal."""
    length = len(error_signal)
    center_idx = int(length / 2)

    # crop the reference signal such that it shows the same region as the new
    # error signal
    idx_shift = int(length * (1 / zoom_factor / 2))
    zoomed_ref = reference_signal[center_idx - idx_shift:center_idx + idx_shift]

    # correlation is slow on red pitaya --> use at maximum 4096 points
    skip_factor = int(len(zoomed_ref) / 4096)
    if skip_factor < 1:
        skip_factor = 1
    zoomed_ref = zoomed_ref[::skip_factor]

    # now sample the error signal down to the same length as the zoomed
    # reference signal
    downsampled_error_signal = resample(error_signal, len(zoomed_ref))

    correlation = correlate(zoomed_ref, downsampled_error_signal)
    """plt.plot(downsampled_error_signal)
    plt.plot(zoomed_ref)
    plt.show()"""


    """plt.plot(correlation)
    plt.show()"""

    shift = np.argmax(correlation)
    shift = (shift - len(zoomed_ref)) / len(zoomed_ref) * 2 / zoom_factor

    return shift, zoomed_ref, downsampled_error_signal


def get_lock_point(error_signal, x0, x1):
    """Calculates parameters for the autolock based on the initial error signal.

    Takes the `error_signal` and two points (`x0` and `x1`) as arguments. The
    points are the points selected by the user, and we know that we want to
    lock between them.
    """
    length = len(error_signal)

    # the data that is between the user-selected bounds
    cropped_data = np.array(error_signal[x0:x1])

    min_idx = np.argmin(cropped_data)
    max_idx = np.argmax(cropped_data)

    # the y value that is between minimum and maximum
    mean_signal = np.mean([cropped_data[min_idx], cropped_data[max_idx]])
    idxs = sorted([min_idx, max_idx])
    slope_data = np.array(cropped_data[idxs[0]:idxs[1]]) - mean_signal

    zero_idx = x0 + np.min(idxs) + np.argmin(np.abs(slope_data))

    # roll the error signal such that the target lock point is exactly in the
    # center
    roll = -int(zero_idx - (length/2))
    rolled_error_signal = np.roll(error_signal, roll)
    # set all the rolled points to zero such that they don't contribute
    # in the correlation
    if roll < 0:
        rolled_error_signal[roll:] = 0
    else:
        rolled_error_signal[:roll] = 0

    target_slope_rising = max_idx > min_idx
    target_zoom = 16384 / (idxs[1] - idxs[0]) / 1.5

    return mean_signal, target_slope_rising, target_zoom, rolled_error_signal


def control_signal_has_correct_amplitude(control_signal, amplitude_target):
    # we ignore some points as sometimes the triggering is not 100%ly
    # correct, i.e. at the beginning or end of the sample we have a glitch
    edge = int(0.4 * len(control_signal))
    control_signal_center = control_signal[edge:-edge]
    control_signal_amplitude = (
        np.max(control_signal_center) - np.min(control_signal_center)
    ) / len(control_signal_center) * len(control_signal) / 16384

    return np.abs(control_signal_amplitude - amplitude_target) / control_signal_amplitude < 0.1


def convert_channel_mixing_value(value):
    if value <= 0:
        a_value = 128
        b_value = 128 + value
    else:
        a_value = 127 - value
        b_value = 128

    return a_value, b_value


def combine_error_signal(error_signals, dual_channel, channel_mixing, chain_factor_width=8):
    if not dual_channel:
        return error_signals[0]

    a_factor, b_factor = convert_channel_mixing_value(channel_mixing)

    return [
        (a_factor * a + b_factor * b) >> chain_factor_width
        for a, b in zip(*error_signals)
    ]