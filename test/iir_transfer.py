import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

from migen.fhdl import verilog
from migen.fhdl.std import *

from transfer import ResetTransfer, CsrTransfer
from iir_coeffs import make_filter, quantize_filter

from gateware.iir import Iir


def get_params(typ="PI", f=1., k=1., g=1., shift=None, width=25, fs=1., q=.5):
    f *= np.pi/fs
    b, a = make_filter(typ, k=k, f=f, g=g, q=q)
    b, a, shift = quantize_filter(b, a, shift, width)
    p = {}
    for i, (ai, bi) in enumerate(zip(a, b)):
        p["a%i" % i] = ai
        p["b%i" % i] = bi
    return p, shift


def _main2():
    from migen.fhdl import verilog
    from migen.sim.generic import run_simulation
    from matplotlib import pyplot as plt
    import numpy as np

    iir = Iir()
    print(verilog.convert(iir, ios={iir.x, iir.y,
        iir.mode_in, iir.mode_out}))

    n = 10000
    x = np.zeros(n)
    x[n/4:n/2] = .5
    x[n/2:3*n/4] = -x[n/4:n/2]
    tb = TB(x, order=1, mode="pipelined")
    tb.params, shift = get_params("PI", f=5e-4, k=1., g=1e4,
            width=flen(tb.iir.c["a1"]))
    tb.params["a0"] = shift
    #print(verilog.convert(tb))
    run_simulation(tb, vcd_name="iir.vcd")
    plt.plot(tb.x)
    plt.plot(tb.y)
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
	b, a = make_filter("PI", f=8e-6, k=1.-1e-5, g=1e20)
	#b, a = make_filter("IHO", f=.05, k=.04, g=10., q=10.)
	#b, a = make_filter("LP2", f=.002, k=20., q=1.)
	#b, a = make_filter("P", k=30)
	#b, a = make_filter("I", f=.5, k=.1)
	#b, a = make_filter("I", f=.000008, k=1.)
	#b, a = make_filter("NOTCH", f=.02, k=10., q=.5)
	#tb = ResetTransfer(b, a, form="tdf2", **kwargs)
	tb = CsrTransfer(b, a, **kwargs)
	print(tb.b, tb.a)
	tb.analyze()
	plt.show()

if __name__ == "__main__":
    _pid()
    #_main2()
