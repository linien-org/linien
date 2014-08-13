from math import log

from migen.fhdl.std import *


class IIR(Module):
    """Infinite Impolse Response Filter

    Transposed direct form II:

      * canonical wrt delay (but we use double width delays to have
        less truncation issues making it less canonical)
      * multipliers get their inputs early
      * no input scaling
      * modulo math works for us
      * good truncation noise behaviour
      * compared to DFI (the other form with good truncation and
        overflow behaviour) there is no central large adder.
    """
    def __init__(self, width=18, order=2, saturate=True,
            form="tdf2"):
        self.x = Signal((width, True))
        self.y = Signal((width, True))
        self.b = [Signal((width, True)) for i in range(order + 1)]
        self.a = [Signal((width, True)) for i in range(order + 1)]
        zwidth = 2*width
        self.scale = Signal(max=zwidth, reset=width - 2)
        self.saturate = Signal(2)
        self.width = width
        self.order = order

        ##

        self.comb += self.scale.eq(self.a[0])

        if form == "tdf2":
            z0 = 0
            for i in reversed(range(order + 1)):
                z = Signal((zwidth, True))
                zb = self.b[i]*self.x
                za = self.a[i]*self.y if i > 0 else 0
                self.comb += z.eq(z0 + zb - za)
                z0 = Signal((zwidth, True))
                self.sync += z0.eq(z)
            self.latency = 0
        elif form == "tdf2a": # systolic form
            z0 = 0
            for i in reversed(range(order + 1)):
                z = Signal((zwidth, True))
                self.sync += z.eq(z0 + self.b[i]*self.x)
                z0 = z
            for i in reversed(range(1, order + 1)):
                z = Signal((zwidth, True))
                self.sync += z.eq(z0 - self.a[i]*self.y)
                z0 = z
            self.latency = order + 1
        elif form == "df1":
            z0 = 0
            x, y = self.x, self.y
            for i in range(order + 1):
                z0 = z0 + self.b[i]*x
                if i > 0:
                    z0 = z0 - self.a[i]*y
                xi = Signal((width, True))
                yi = Signal((width, True))
                self.sync += xi.eq(x), yi.eq(y)
                x, y = xi, yi
            z = Signal((zwidth, True))
            self.comb += z.eq(z0)
            self.latency = 0
        elif form == "tdf2b":
            seq = []
            x = Signal((width, True))
            zi = [Signal((zwidth, True)) for i in range(order + 1)] + [0]
            for i in reversed(range(order + 1)):
                seq.append((zi[i], zi[i + 1], x, self.b[i]))
                if i > 0:
                    am = Signal((width, True))
                    self.comb += am.eq(-self.a[i])
                    seq.append((zi[i], zi[i], self.y, am))
            z = zi[0]
            i = Signal(max=len(seq), reset=len(seq) - 1)
            n, m, p, q = (Array(_)[i] for _ in zip(*seq))
            self.sync += [
                    i.eq(i + 1),
                    If(i == len(seq) - 1,
                        i.eq(0),
                        x.eq(self.x),
                    ),
                    n.eq(m + p*q),
                    ]
            self.latency = len(seq) + 1
        else:
            raise NotImplementedError("form {} not supported".format(form))

        limit = Signal((zwidth, True), reset=(1<<(zwidth - 2)) - 1)
        self.sync += [
                If(self.scale > width,
                    limit.eq((1<<(zwidth - 1)) - 1),
                ).Else(
                    limit.eq((1<<(width - 1 + self.scale)) - 1),
                )]
        self.comb += self.saturate.eq(Cat(z < -limit, z >= limit))
        self.comb += self.y.eq(z>>self.scale)
        if saturate:
            limit = 1<<width - 1
            self.comb += [
                    If(self.saturate[0], self.y.eq(-limit)),
                    If(self.saturate[1], self.y.eq(limit - 1)),
                    ]

    def _wide_mul(self, p, q, a, b, w=18):
        w -= 1
        # TODO sign extend the middle two steps
        yield p, 0, Cat(a[:w], 0), Cat(b[:w], 0)
        yield p[w:], p[w:], a[w:], Cat(a[:w], 0)
        yield p[w:], p[w:], Cat(a[:w], 0), b[w:]
        yield p[2*w:], p[2*w:], a[w:], b[w:]
