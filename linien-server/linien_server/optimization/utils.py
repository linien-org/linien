# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

import numpy as np
from scipy import optimize, stats

# after the line was centered, its width will be 1/FINAL_ZOOM_FACTOR of the
# view.
FINAL_ZOOM_FACTOR = 20


def get_max_slope(signal, final_zoom_factor):
    line_width = len(signal) / final_zoom_factor
    window_width = 1.5 * line_width
    center = len(signal) / 2
    range_around_center = [
        round(center - (window_width / 2)),
        round(center + (window_width / 2)),
    ]
    crop = signal[range_around_center[0] : range_around_center[1]]

    idx = list(sorted([np.argmax(crop), np.argmin(crop)]))

    crop_of_crop = crop[idx[0] : idx[1]]

    slope, intercept, r_value, p_value, std_err = stats.linregress(
        list(range(len(crop_of_crop))), crop_of_crop
    )

    # x_diff = np.abs(idx[0] - idx[1])
    # return abs(slope * x_diff)
    return abs(slope)


def calculate_spectrum_from_iq(i, q, phase):
    return np.array(i) * np.cos(phase / 360 * 2 * np.pi) + np.array(q) * np.sin(
        phase / 360 * 2 * np.pi
    )


def optimize_phase_from_iq(i, q, final_zoom_factor):
    def iq2slope(phase):
        calculated = calculate_spectrum_from_iq(i, q, phase)
        return get_max_slope(calculated, final_zoom_factor)

    min_result = optimize.minimize_scalar(
        lambda phase: -1 * iq2slope(phase), method="Bounded", bounds=(0, 360)
    )
    assert min_result.success

    return min_result.x, abs(min_result.fun)
