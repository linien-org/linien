import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

from migen.fhdl import verilog
from migen.fhdl.std import *

from transfer import ResetTransfer, CsrTransfer
from iir_coeffs import make_filter

from gateware.iir import Iir


def get_params(shift=None, width=25, **kwargs):
    b, a = make_filter(**kwargs)
    b, a, shift = quantize_filter(b, a, shift, width)
    params = {}
    for i, (ai, bi) in enumerate(zip(a, b)):
        params["a%i" % i] = ai
        params["b%i" % i] = bi
    params["a0"] = shift
    return params


def _main2():
    iir = Iir()
    print(verilog.convert(iir, ios={iir.x, iir.y,
        iir.mode_in, iir.mode_out}))

    n = 10000
    x = np.zeros(n)
    x[n/4:n/2] = .1
    x[n/2:3*n/4] = -x[n/4:n/2]

    b, a = make_filter("PI", f=2e-5, k=1-1e-5, g=1e20)
    tb = CsrTransfer(b, a, amplitude=x, order=1, mode="pipelined")
    #print(verilog.convert(tb.tb))
    x, y = tb.tb.run(vcd_name="iir.vcd")
    plt.plot(x)
    plt.plot(y)
    plt.show()


def _iir():
	kwargs = dict(width=18, form="tdf2", saturate=True,
			samples=1<<12)
	b, a = scipy.signal.iirdesign(.1, .2, 3., 23)
	b *= 100
	tb = ResetTransfer(b, a, **kwargs)
	print(verilog.convert(tb, ios={tb.dut.x, tb.dut.y}))
	print(tb.b, tb.a)
	ResetTransfer(b, a, **kwargs).analyze()
	plt.show()


def _pid():
	kwargs = dict(samples=1<<14, amplitude=.8)
	#b, a = make_filter("LP", f=.1, k=500.)
	b, a = make_filter("PI", f=2e-5, k=1.-1e-5, g=1e20)
	#b, a = make_filter("IHO", f=.05, k=.04, g=10., q=10.)
	#b, a = make_filter("LP2", f=.002, k=20., q=1.)
	#b, a = make_filter("P", k=30)
	#b, a = make_filter("I", f=.5, k=.1)
	#b, a = make_filter("I", f=.000008, k=1.)
	#b, a = make_filter("NOTCH", f=.02, k=10., q=.5)
	#tb = ResetTransfer(b, a, form="tdf2", **kwargs)
	tb = CsrTransfer(b, a, **kwargs)
	#print(tb.b, tb.a)
	tb.analyze()
	plt.show()

if __name__ == "__main__":
    _pid()
    #_main2()
