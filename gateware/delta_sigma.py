from migen.fhdl.std import *
from migen.bank.description import *
from migen.sim.generic import run_simulation, StopSimulation


class DeltaSigma(Module):
    def __init__(self, width=24):
        self.data = Signal(width)
        self.out = Signal()

        ###

        delta = Signal(2)
        sigma = Signal(width + 2)
        self.comb += delta.eq(Cat(sigma[-1], sigma[-1]))
        self.sync += sigma.eq((self.data + (delta << width)) + sigma)
        self.comb += self.out.eq(sigma[-1])


class DeltaSigmaCSR(Module, AutoCSR):
    def __init__(self, out, **kwargs):
        for i, o in enumerate(out):
            ds = DeltaSigma(**kwargs)
            setattr(self.submodules, "data%i" % i, ds)
            cs = CSRStorage(flen(ds.data), name="data%i" % i,
                    atomic_write=True)
            setattr(self, "r_data%i" % i, cs)
            self.comb += ds.data.eq(cs.storage), o.eq(ds.out)


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.dut = DeltaSigma(**kwargs)
        n = 1<<flen(self.dut.data)
        self.x = [j for j in range(n) for i in range(n)]
        self.y = []
        self.gen = iter(self.x)

    def do_simulation(self, selfp):
        try:
            selfp.dut.data = next(self.gen)
        except StopIteration:
            pass
        self.y.append(selfp.dut.out)
        if len(self.y) == len(self.x):
            raise StopSimulation


if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt
    tb = TB(width=8)
    run_simulation(tb)
    x, y = np.array(tb.x), np.array(tb.y)
    n = 1<<flen(tb.dut.data)
    plt.plot(x.reshape(-1, n).mean(1))
    plt.plot(y.reshape(-1, n).mean(1)*n)
    #plt.plot(np.repeat(n
    plt.show()
