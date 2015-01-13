# (C) Roberr Jordens <jordens@gmail.com> 2014, 2015

import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

from migen.fhdl import verilog
from migen.fhdl.std import *

from transfer import ResetTransfer, CsrTransfer
from iir_coeffs import make_filter

from gateware.iir import Iir


def _iir2():
    iir = Iir()
    print(verilog.convert(iir, ios={iir.x, iir.y}))

    n = 10000
    x = np.zeros(n)
    x[n/4:n/2] = .1
    x[n/2:3*n/4] = -x[n/4:n/2]

    b, a = make_filter("PI", f=2e-2, k=1., g=1e20)
    #tb = CsrTransfer(b, a, Iir(order=len(b) - 1), x)
    tb = CsrTransfer(b, a, Iir(order=len(b) - 1), x)
    #print(verilog.convert(tb.tb))
    x, y = tb.tb.run(vcd_name="iir.vcd")
    plt.plot(x)
    plt.plot(y)
    plt.show()


def _pid():
    #b, a = make_filter("LP", f=1e-3, k=4000.)
    #b, a = make_filter("PI", f=2e-5, k=1-1e-5, g=1e20)
    b, a = make_filter("HP", f=2e-8, k=.999, g=1e20)
    #b, a = make_filter("IHO", f=.05, k=.04, g=10., q=10.)
    #b, a = make_filter("LP2", f=.002, k=20., q=1.)
    #b, a = make_filter("P", k=30)
    #b, a = make_filter("I", f=.5, k=.1)
    #b, a = make_filter("I", f=.000008, k=1.)
    #b, a = make_filter("NOTCH", f=.02, k=10., q=.5)
    #tb = ResetTransfer(b, a, form="tdf2", **kwargs)
    tb = CsrTransfer(b, a, Iir(#mode="iterative",
        coeff_width=2*18-1, width=25, shift=2*18-3,
        order=len(b) - 1), amplitude=.2, samples=1<<14)
    print(tb.b, tb.a)
    tb.analyze()
    plt.show()


if __name__ == "__main__":
    #_iir2()
    _pid()
