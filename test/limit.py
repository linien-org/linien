# (C) Roberr Jordens <jordens@gmail.com> 2014, 2015

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
