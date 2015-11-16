# Copyright 2014-2015 Robert Jordens <jordens@gmail.com>
#
# This file is part of redpid.
#
# redpid is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# redpid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with redpid.  If not, see <http://www.gnu.org/licenses/>.

from migen import *
from misoc.interconnect.csr import CSRStatus, AutoCSR


class Filter(Module, AutoCSR):
    def __init__(self, width):
        self.x = Signal((width, True))
        self.y = Signal((width, True))

        self.hold = Signal()
        self.clear = Signal()
        self.error = Signal()

        if False:
            self.y_current = CSRStatus(width)
            self.comb += self.y_current.status.eq(self.y)
