import numpy as np


def update_control_signal_history(history, to_plot, is_locked):
    if not to_plot:
        return history

    # FIXME: implement max_length
    error_signal, control_signal = to_plot

    if is_locked:
        history.append(np.mean(control_signal))

    return history