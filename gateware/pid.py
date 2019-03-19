from migen import Module, If, Signal
from misoc.interconnect.csr import CSRStorage, AutoCSR


class PID(Module, AutoCSR):
    def __init__(self, width=14, signal_width=28):
        self.width = width
        self.signal_width = signal_width

        self.input = Signal((width, True))

        self.max_pos = (1 << (width - 1)) - 1
        self.max_neg = (-1 * self.max_pos) - 1

        self.calculate_error_signal()
        self.calculate_p()
        self.calculate_i()
        self.calculate_d()
        self.calculate_sum()

    def calculate_error_signal(self):
        self.setpoint = CSRStorage(self.width)
        setpoint_signed = Signal((self.width, True))
        self.comb += [
            setpoint_signed.eq(self.setpoint.storage)
        ]

        self.error = Signal((self.width + 1, True))

        self.sync += [
            self.error.eq(
                self.input - self.setpoint.storage
            )
        ]

    def calculate_p(self):
        self.kp = CSRStorage(self.width)
        kp_signed = Signal((self.width, True))
        self.comb += [
            kp_signed.eq(self.kp.storage)
        ]

        kp_mult = Signal((self.width * 2, True))
        self.comb += [
            kp_mult.eq(self.error * kp_signed)
        ]

        self.output_p = Signal((self.width + 2, True))
        self.sync += [
            self.output_p.eq(
                kp_mult[-(self.width + 2):]
            )
        ]

        self.kp_mult = kp_mult

    def calculate_i(self):
        self.ki = CSRStorage(self.width)
        self.reset = CSRStorage()

        ki_signed = Signal((self.width, True))
        self.comb += [
            ki_signed.eq(self.ki.storage)
        ]

        self.ki_mult = Signal((self.width * 2, True))

        self.sync += [
            self.ki_mult.eq(
                self.error * ki_signed
            )
        ]

        self.int_reg = Signal((32, True))
        self.int_sum = Signal((33, True))
        self.int_shr = Signal((self.width, True))

        self.comb += [
            self.int_sum.eq(
                self.ki_mult + self.int_reg
            ),
            self.int_shr.eq(
                self.int_reg[18:]
            )
        ]

        self.sync += [
            If(self.reset.storage,
                self.int_reg.eq(0)
            ).Elif((self.int_sum[-1] == 0) & (self.int_sum[-2] == 1), # positive saturation
                self.int_reg.eq(0x7FFFFFFF)
            ).Elif((self.int_sum[-1] == 1) & (self.int_sum[-2] == 0), # negative saturation
                self.int_reg.eq(0x80000000)
            ).Else(
                self.int_reg.eq(self.int_sum)
            )
        ]

    def calculate_d(self):
        self.kd = CSRStorage(self.width)
        kd_mult = Signal((29, True))
        kd_reg = Signal((19, True))
        kd_reg_r = Signal((19, True))
        self.kd_reg_s = Signal((20, True))
        kd_signed = Signal((self.width, True))

        self.comb += [
            kd_signed.eq(self.kd.storage),
            kd_mult.eq(self.error * kd_signed)
        ]

        self.sync += [
            kd_reg.eq(kd_mult[10:29]),
            kd_reg_r.eq(kd_reg),
            self.kd_reg_s.eq(kd_reg - kd_reg_r)
        ]


    def calculate_sum(self):
        self.pid_sum = Signal((33, True))
        self.pid_out = Signal((self.width, True))

        _or = self.pid_sum[13:32-1] > 0
        _and = 1
        bits = list(n + 13 for n in range(33-13))
        for bit in bits:
            _and = _and & self.pid_sum[bit]
        _and = _and == 0

        self.sync += [
            If((self.pid_sum[-1] == 0) & (_or), # positive overflow
                self.pid_out.eq(self.max_pos)
            ).Elif((self.pid_sum[-1] == 1) & (_and), # negative overflow
                self.pid_out.eq(self.max_neg)
            ).Else(
                self.pid_out.eq(self.pid_sum[:14])
            )
            #self.pid_out.eq(pid_sum[:self.width])
        ]

        self.comb += [
            self.pid_sum.eq(
                self.output_p + self.int_shr + self.kd_reg_s
            )
        ]