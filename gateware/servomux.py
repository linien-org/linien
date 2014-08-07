from migen.fhdl.std import *
from migen.bank.description import CSRStorage, AutoCSR


class ServoMux(Module, AutoCSR):
    def __init__(self, adcs, miscs, servos):
        a = Array([0] + [adc.y for adc in adcs])
        self.misc_mux = [Signal(max=len(a)) for m in miscs]
        self.comb += [m.x.eq(a[mmux]) for m, mmux in zip(miscs,
            self.misc_mux)]
        self._misc_mux = CSRStorage(2*len(adcs))
        self.comb += [mm.eq(self._misc_mux.storage[i*2:(i+1)*2])
                for i, mm in enumerate(self.misc_mux)]

        b = Array([0]
                + [adc.y for adc in adcs]
                + [misc.y for misc in miscs]
                + [servo.y for servo in servos])
        self.servo_mux = [Signal(max=len(b)) for s in servos]
        servo_in = [Signal((flen(s.x), True)) for s in servos]
        self.comb += [si.eq(b[mux]) for si, mux in zip(servo_in,
            self.servo_mux)]
        self.servo_sign = [Signal() for s in servos]
        self.servo_set = [Signal((flen(s.x), True)) for s in servos]
        self.comb += [
                If(sig, ser.x.eq(sin-setp),
                ).Else( ser.x.eq(-sin-setp),
                ) for ser, sig, setp, sin in zip(servos, self.servo_sign,
                    self.servo_set, servo_in)]
        self.relock_mux = [Signal(max=len(b)) for s in servos]
        self.comb += [servo.relock.x.eq(b[mux]) for servo, mux in zip(servos,
            self.relock_mux)]

        self.hold_in = Signal(len(servos))
        c = Array([0]
                + [servo.relock.hold_out for servo in servos]
                + [self.hold_in[i] for i in range(flen(self.hold_in))]
                )
        self.hold_mux = [Signal(max=len(c)) for s in servos]
        self.comb += [servo.hold.eq(c[mux]) for servo, mux in zip(servos,
            self.hold_mux)]

        for i, servo in enumerate(servos):
            csr = CSRStorage(8, name="servo{}_mux".format(i))
            setattr(self, "_servo{}_mux".format(i), csr)
            self.comb += [
                    self.servo_mux[i].eq(csr.storage[0:3]),
                    self.relock_mux[i].eq(csr.storage[3:6]),
                    self.servo_sign[i].eq(csr.storage[6]),
                    ]
            csr = CSRStorage(16, name="servo{}_set".format(i))
            setattr(self, "_servo{}_set".format(i), csr)
            self.comb += self.servo_set[i].eq(csr.storage)

            csr = CSRStorage(3, name="servo{}_hold".format(i))
            setattr(self, "_servo{}_hold".format(i), csr)
            self.comb += self.hold_mux[i].eq(csr.storage)
