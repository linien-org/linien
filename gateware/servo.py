from migen.fhdl.std import *
from migen.bank.description import CSRStorage, CSRStatus, AutoCSR

from iir import Iir
from limit import Limit
from relock import Relock
from sweep import Sweep


class Servo(Module, AutoCSR):
    def __init__(self, width=16):
        self.x = Signal((width, True))
        self.submodules.iir0 = Iir(x=width, y=width, order=2,
                width=35, intermediate_width=70, a0_shift=26,
                mode="iterative")
        self.submodules.iir1 = Iir(x=width, y=width, order=1,
                width=35, intermediate_width=70, a0_shift=26,
                mode="pipelined")
        self.submodules.iir2 = Iir(x=width, y=width, order=1,
                width=35, intermediate_width=70, a0_shift=26,
                mode="pipelined")
        self.submodules.iir3 = Iir(x=width, y=width, order=1,
                width=35, intermediate_width=70, a0_shift=26,
                mode="pipelined")
        self.submodules.sweep = Sweep()
        self.submodules.relock = Relock()
        self.submodules.limit = Limit()
        self.lo = Signal((width, True))
        self.lo_atten = Signal(max=16)
        self.mod = Signal((width, True))
        self.mod_atten = Signal(max=16)
        self.y = Signal((width, True))
        self.hold = Signal()
        self.comb += [
                self.iir0.x.eq(self.x),
                self.iir1.x.eq(self.iir0.y),
                self.iir2.x.eq(self.iir1.y),
                self.iir3.x.eq(self.iir2.y),
                self.iir0.railed.eq(self.limit.railed),
                self.iir1.railed.eq(self.limit.railed),
                self.iir2.railed.eq(self.limit.railed),
                self.iir3.railed.eq(self.limit.railed),
                self.iir0.hold.eq(self.hold | self.relock.hold_out),
                self.iir1.hold.eq(self.hold | self.relock.hold_out),
                self.iir2.hold.eq(self.hold | self.relock.hold_out),
                self.iir3.hold.eq(self.hold | self.relock.hold_out),
                self.relock.hold_in.eq(self.hold),
                self.relock.railed.eq(self.limit.railed),
                self.limit.x.eq(self.iir3.y + self.sweep.y + self.relock.y
                    + (self.lo>>self.lo_atten) +
                    (self.mod>>self.mod_atten)),
                self.y.eq(self.limit.y),
                ]
        self._bypass = CSRStorage(4)
        self.comb += [Cat(*(i.bypass for i in 
            (self.iir0, self.iir1, self.iir2, self.iir3))
            ).eq(self._bypass.storage)]
        self._stop = CSRStorage(6)
        self.comb += [Cat(*(i.stop for i in 
            (self.iir0, self.iir1, self.iir2, self.iir3, self.sweep,
                self.relock))).eq(self._stop.storage)]
        for i, iir in enumerate((self.iir0, self.iir1, self.iir2, self.iir3)):
            for n, c in iir.coeffs.items():
                csr = CSRStorage(flen(c), name="iir{}_{}".format(i, n))
                setattr(self, "_iir{}_{}".format(i, n), csr)
                self.comb += c.eq(csr.storage)
        for reg, name in [
                (self.lo_atten, "lo_atten"),
                (self.mod_atten, "mod_atten"), 
                (self.sweep.maxval, "sweep_maxval"),
                (self.sweep.minval, "sweep_minval"),
                (self.sweep.step, "sweep_step"),
                (self.relock.maxval, "relock_maxval"),
                (self.relock.minval, "relock_minval"),
                (self.relock.step, "relock_step"),
                (self.limit.maxval, "limit_maxval"),
                (self.limit.minval, "limit_minval"),
                ]:
            csr = CSRStorage(flen(reg), name=name)
            setattr(self, "_{}".format(name), csr)
            self.comb += reg.eq(csr.storage)


class TB(Module):
    def __init__(self, **kwargs):
        self.submodules.servo = Servo(**kwargs)

    def do_simulation(self, s):
        pass


def main():
    from migen.fhdl import verilog
    from migen.sim.generic import Simulator, TopLevel

    s = Servo()
    print(verilog.convert(s, ios=set()))

    n = 200
    tb = TB()
    sim = Simulator(tb, TopLevel("servo.vcd"))
    sim.run(n+20)


if __name__ == "__main__":
    main()
