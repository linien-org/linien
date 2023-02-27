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

ACQUISITION_PORT = 19321
DEFAULT_SERVER_PORT = 18862
DEFAULT_SWEEP_SPEED = (125 * 2048) << 6
# IMPORTANT: DEFAULT_COLORS and N_COLORS have to be here, not in client.config
# because the server needs them and shouldn't import client config as it requires
# additional packages
DEFAULT_COLORS = [
    (200, 0, 0, 200),
    (0, 200, 0, 200),
    (0, 0, 200, 200),
    (200, 200, 0, 200),
    (200, 0, 200, 200),
]
N_COLORS = len(DEFAULT_COLORS)
