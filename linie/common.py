import numpy as np
from time import time


def update_control_signal_history(history, to_plot, is_locked, max_time_diff):
    if not to_plot:
        return history

    # FIXME: implement max_length
    error_signal, control_signal = to_plot
    now = time()

    if is_locked:
        history['values'].append(np.mean(control_signal))
        history['times'].append(time())

    # truncate
    while len(history['values']) > 0:
        if time() - history['times'][0] > max_time_diff:
            history['times'].pop(0)
            history['values'].pop(0)
            continue
        break

    return history