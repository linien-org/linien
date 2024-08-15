# This file is part of Linien and based on redpid.
#
# Copyright (C) 2016-2024 Linien Authors (https://github.com/linien-org/linien#license)
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

from migen import Array, Module, Signal


class Decimate(Module):
    def __init__(self, max_decimation):
        self.decimation = Signal(max_decimation)

        self.decimation_counter = Signal(max_decimation)
        self.sync += [self.decimation_counter.eq(self.decimation_counter + 1)]

        self.output = Signal(1)

        self.sync += [self.output.eq(Array(self.decimation_counter)[self.decimation])]
