from migen.fhdl.std import *
from migen.bank.description import *
from migen.sim.generic import run_simulation, StopSimulation


class DeltaSigma(Module):
    def __init__(self, width=12):
        self.data = Signal(width)
        self.out = Signal()

        ###

        delta = Signal(width + 1)
        sigma = Signal(width + 1)
        self.comb += delta.eq(self.out << width)
        self.sync += sigma.eq(self.data - delta + sigma)
        self.comb += self.out.eq(sigma[-1])


class DeltaSigma2(Module):
    def __init__(self, width=12):
        self.data = Signal(width)
        self.out = Signal()

        ###

        delta = Signal(width + 1)
        i1 = Signal(width + 3)
        i2 = Signal(width + 3)
        sigma1 = Signal(width + 3)
        sigma2 = Signal(width + 3)
        self.comb += [
                delta.eq(self.out << width),
                i1.eq(self.data - delta + sigma1),
                i2.eq(i1 - delta + sigma2),
                self.out.eq(sigma2[-1])
        ]
        self.sync += [
                sigma1.eq(i1),
                sigma2.eq(i2)
        ]


class DeltaSigmaCSR(Module, AutoCSR):
    def __init__(self, out, **kwargs):
        for i, o in enumerate(out):
            ds = DeltaSigma(**kwargs)
            self.submodules += ds
            cs = CSRStorage(flen(ds.data), name="data%i" % i)
            # atomic_write=True
            setattr(self, "r_data%i" % i, cs)
            self.sync += ds.data.eq(cs.storage), o.eq(ds.out)


class TB(Module):
    def __init__(self, dut, x):
        self.submodules.dut = dut
        n = 1<<flen(self.dut.data)
        self.x = x
        self.y = []
        self.gen = iter(self.x)

    def do_simulation(self, selfp):
        try:
            selfp.dut.data = next(self.gen)
        except StopIteration:
            pass
        self.y.append(selfp.dut.out)
        if len(self.y) - 2 == len(self.x):
            del self.y[:2]
            raise StopSimulation


if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt
    for dut in DeltaSigma2(15), DeltaSigma(15):
        n = 1<<flen(dut.data)
        #x = [j for j in range(n) for i in range(n)]
        x = (.5+.4*np.cos(.001*2*np.pi*np.arange(1<<14)))*(n-1)
        tb = TB(dut, x)
        run_simulation(tb)
        #x = np.array(tb.x).reshape(-1, n)
        #y = np.array(tb.y).reshape(-1, n)
        #plt.plot(x[:, 0], x[:, 0] - y.sum(1))
        #plt.plot(y.ravel())
        plt.psd(np.array(tb.y), detrend=plt.mlab.detrend_mean, NFFT=4096*2)
        plt.xscale("log")
    plt.show()
