import numpy as np
from time import time
from scipy.signal import correlate, resample


def update_control_signal_history(history, to_plot, is_locked, max_time_diff):
    if not to_plot:
        return history

    error_signal, control_signal = to_plot
    now = time()

    if is_locked:
        history['values'].append(np.mean(control_signal))
        history['times'].append(time())
    else:
        history['values'] = []
        history['times'] = []

    # truncate
    while len(history['values']) > 0:
        if time() - history['times'][0] > max_time_diff:
            history['times'].pop(0)
            history['values'].pop(0)
            continue
        break

    return history


def determine_shift_by_correlation(zoom_factor, reference_signal, error_signal):
    length = len(error_signal)
    center_idx = int(length / 2)

    idx_shift = int(length * (1 / zoom_factor / 2))
    zoomed_ref = reference_signal[center_idx - idx_shift:center_idx + idx_shift]

    # correlation is slow on red pitaya --> use at maximum 4096 points
    skip_factor = int(len(zoomed_ref) / 4096)
    if skip_factor < 1:
        skip_factor = 1

    zoomed_ref = zoomed_ref[::skip_factor]
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
    cropped_data = np.array(error_signal[x0:x1])
    min_idx = np.argmin(cropped_data)
    max_idx = np.argmax(cropped_data)

    mean_signal = np.mean([cropped_data[min_idx], cropped_data[max_idx]])
    idxs = sorted([min_idx, max_idx])
    slope_data = np.array(cropped_data[idxs[0]:idxs[1]]) - mean_signal

    zero_idx = x0 + np.min(idxs) + np.argmin(np.abs(slope_data))
    target_slope_rising = max_idx > min_idx
    target_zoom = 16384 / (idxs[1] - idxs[0]) / 1.5

    length = len(error_signal)
    rolled_error_signal = np.roll(error_signal, -int(zero_idx - (length/2)))

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
        a_value = 128 + value
        b_value = 128
    else:
        a_value = 128
        b_value = 127 - value

    return a_value, b_value


def combine_error_signal(error_signals, dual_channel, channel_mixing, chain_factor_width=8):
    if not dual_channel:
        return error_signals[0]

    a_factor, b_factor = convert_channel_mixing_value(channel_mixing)

    return [
        (a_factor * a + b_factor * b) >> chain_factor_width
        for a, b in zip(*error_signals)
    ]