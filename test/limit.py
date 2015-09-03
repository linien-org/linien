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

class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.limit = Limit(**kwargs)
        self.x = []
        self.y = []

    def do_simulation(self, selfp):
        c = selfp.simulator.cycle_counter
        if c == 0:
            selfp.limit.maxval = 1<<10
            selfp.limit.minval = -(1<<10)
        selfp.limit.x = -2*selfp.limit.maxval + (c << 6)
        self.x.append(selfp.limit.x)
        self.y.append(selfp.limit.y)


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import run_simulation
    import matplotlib.pyplot as plt

    s = Limit()
    print(verilog.convert(s, ios=set()))

    n = 1<<6
    tb = TB()
    run_simulation(tb, vcd_name="limit.vcd", ncycles=n)
    plt.plot(tb.x)
    plt.plot(tb.y)
    plt.show()


if __name__ == "__main__":
    main()
