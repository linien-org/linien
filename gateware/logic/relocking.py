# Copyright 2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
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

from migen import If, Module, Signal
from misoc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage


class RelockWatcher(Module, AutoCSR):
    def __init__(self, width=14, coeff_width=14):
        self.locked = Signal()
        self.should_watch = Signal()

        self.error_signal = Signal((width, True))
        self.control_signal = Signal((width, True))
        self.monitor_signal = Signal((width, True))

        self.lock_lost = CSRStatus()

        channels = (
            ("control", self.control_signal),
            ("error", self.error_signal),
            ("monitor", self.monitor_signal),
        )
        lock_lost_signal = Signal()
        for channel_name, channel in channels:
            channel_watcher = RelockWatcherChannel(width)
            setattr(self.submodules, channel_name, channel_watcher)
            should_watch_name = "should_watch_" + channel_name
            should_watch_csr = CSRStorage(name=should_watch_name)
            setattr(self, should_watch_name, should_watch_csr)
            min_name = "min_" + channel_name
            min_csr = CSRStorage(name=min_name)
            setattr(self, min_name, min_csr)
            max_name = "max_" + channel_name
            max_csr = CSRStorage(name=max_name)
            setattr(self, max_name, max_csr)

            self.comb += [
                channel_watcher.input.eq(channel),
                channel_watcher.locked.eq(self.locked),
                channel_watcher.should_watch.eq(should_watch_csr.storage),
                channel_watcher.min.eq(min_csr.storage),
                channel_watcher.max.eq(max_csr.storage),
            ]

            lock_lost_signal |= channel_watcher.lock_lost

        self.comb += [self.lock_lost.status.eq(lock_lost_signal)]


class RelockWatcherChannel(Module):
    def __init__(self, width):
        self.locked = Signal()
        self.lock_lost = Signal()

        self.should_watch = Signal()
        self.min = Signal((width, True))
        self.max = Signal((width, True))
        self.input = Signal((width, True))

        self.sync += [
            If(
                self.locked & self.should_watch,
                If(
                    (self.input > self.max) | (self.input < self.min),
                    self.lock_lost.eq(1),
                ),
            ).Else(self.lock_lost.eq(0))
        ]
