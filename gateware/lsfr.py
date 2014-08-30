from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import AutoCSR, CSRStorage


class LFSR(Module):
    """many-to-one (external xor, fibonacci style)
    xnor (exclude all-ones)
    no extended sequence
    """
    def __init__(self, n=31, taps=[27, 30]):
        self.o = Signal()

        ###

        state = Signal(n)
        self.comb += self.o.eq(~optree("^", [state[i] for i in taps]))
        self.sync += Cat(state).eq(Cat(self.o, state))


class LFSRGen(Module, AutoCSR):
    def __init__(self, width, n=31):
        y = Signal((width, True))
        self.signal_out = y,
        self.signal_in = ()
        self.state_in = ()
        self.state_out = ()

        self.r_bits = CSRStorage(bits_for(width))

        taps = {
                7: (6, 5),
                15: (14, 13),
                31: (30, 27),
                63: (62, 61),
        }[n]

        self.submodules.gen = LFSR(n, taps)
        cnt = Signal(max=width + 1)
        store = Signal(width)
        self.sync += [
                store.eq(Cat(self.gen.o, store)),
                cnt.eq(cnt + 1),
                If(cnt == self.r_bits.storage,
                    cnt.eq(1),
                    y.eq(store),
                    store.eq(Replicate(self.gen.o, flen(store)))
                )
        ]



class _TB(Module):
    def __init__(self, dut):
        self.submodules.dut = dut
        self.o = []

    def do_simulation(self, selfp):
        # print("{0:08x}".format(selfp.dut.o))
        #self.o.append(selfp.dut.o)
        print(selfp.simulator.cycle_counter, selfp.dut.o)
    do_simulation.passive = True


if __name__ == "__main__":
    from migen.fhdl import verilog
    from migen.sim.generic import run_simulation

    lfsr = LFSR(4, [3, 2])
    print(verilog.convert(lfsr, ios={lfsr.o}))

    tb = _TB(LFSR(4, [3, 0]))
    run_simulation(tb, ncycles=20)
    print(tb.o)
   
    raise
    import matplotlib.pyplot as plt
    import numpy as np
    
    o = np.array(tb.o)
    #o = o/2.**flen(tb.dut.o) - .5
    #plt.psd(o)
    plt.hist(o)
    plt.show()
