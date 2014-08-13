import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

from migen.fhdl import verilog
from migen.fhdl.std import *

from transfer import Transfer
from iir_coeffs import make_filter


def _iir():
	kwargs = dict(width=18, form="tdf2", saturate=True,
			samples=1<<12)
	b, a = scipy.signal.iirdesign(.1, .2, 3., 23)
	b *= 100
	tb = Transfer(b, a, **kwargs)
	print(verilog.convert(tb, ios={tb.dut.x, tb.dut.y}))
	print(tb.b, tb.a)
	Transfer(b, a, **kwargs).analyze()
	plt.show()


def _pid():
	kwargs = dict(width=18, form="tdf2", saturate=True,
			samples=1<<14, amplitude=.8)
	#b, a = make_filter("LP", f=.1, k=500.)
	b, a = make_filter("PI", f=.000008, k=1-1e-5, g=1e20)
	#b, a = make_filter("IHO", f=.05, k=.04, g=10., q=10.)
	#b, a = make_filter("LP2", f=.002, k=20., q=1.)
	#b, a = make_filter("P", k=30)
	#b, a = make_filter("I", f=.5, k=.1)
	#b, a = make_filter("I", f=.000008, k=1.)
	#b, a = make_filter("NOTCH", f=.02, k=10., q=.5)
	tb = Transfer(b, a, **kwargs)
	print(tb.b, tb.a)
	tb.analyze()
	plt.show()

if __name__ == "__main__":
	_pid()
