import numpy as np
from scipy import stats, optimize
from matplotlib import pyplot as plt


# after the line was centered, its width will be 1/FINAL_ZOOM_FACTOR of the
# view.
FINAL_ZOOM_FACTOR = 10



def get_max_slope(signal, min_line_width_factor, final_zoom_factor):
    assert 0 <= min_line_width_factor <= 1

    line_width = len(signal) / final_zoom_factor

    interesting_size = round(line_width * min_line_width_factor)

    slopes = []

    x = np.array(list(range(len(signal))))

    shift_step = 0.1 * interesting_size
    for shift_direction in (1, -1):
        for shift_idx in range(1000):
            shift = shift_direction * round(shift_step * shift_idx)
            if abs(shift) > line_width:
                break

            center = round(len(signal) / 2) + shift
            range_around_center = round(interesting_size / 2)
            crop = signal[center - range_around_center:center + range_around_center]

            slope, intercept, r_value, p_value, std_err = stats.linregress(x[:len(crop)], crop)
            slopes.append(abs(slope))

    return np.max(slopes)


def calculate_spectrum_from_iq(i, q, phase):
    return np.array(i) * np.cos(phase / 360 * 2 * np.pi) \
        + np.array(q) * np.sin(phase / 360 * 2 * np.pi)


def optimize_phase_from_iq(i, q, min_line_width_factor, final_zoom_factor):
    def iq2slope(phase):
        calculated = calculate_spectrum_from_iq(i, q, phase)
        return get_max_slope(
            calculated, min_line_width_factor, final_zoom_factor
        )

    min_result = optimize.minimize_scalar(
        lambda phase: -1 * iq2slope(phase),
        method='Bounded',
        bounds=(0, 360)
    )
    assert min_result.success

    return min_result.x, abs(min_result.fun)