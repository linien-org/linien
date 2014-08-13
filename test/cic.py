import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

from migen.fhdl.std import *
from migen.genlib.cic import CIC
from migen.fhdl import verilog
from migen.sim.generic import Simulator


class Transfer(Module):
	def __init__(self, amplitude=1., samples=1<<12, **kwargs):
		self.submodules.dut = CIC(**kwargs)
		i = Signal(max=abs(self.dut.rate))
		self.yi = Signal((flen(self.dut.y), True))
		self.sync += [
				i.eq(i + 1),
				If(i == abs(self.dut.rate) - 1, i.eq(0)),
				self.dut.stb.eq(i == 0),
				If(self.dut.stb, self.yi.eq(self.dut.y)),
				]
		w = 2**(self.dut.width - 1) - 1
		self.x = np.random.uniform(-amplitude*w, amplitude*w,
				samples).astype(np.int)
		self.y = np.empty_like(self.x)
		self.gen = iter(self.x)

	def do_simulation(self, s):
		try:
			s.wr(self.dut.x, next(self.gen))
			self.y[s.cycle_counter] = s.rd(self.yi)
		except StopIteration:
			s.interrupt = True

	def run(self):
		with Simulator(self) as sim:
			sim.run()
		w = 2**(self.dut.width - 1)
		x = self.x[:-self.dut.latency-1]/w
		y = self.y[self.dut.latency+1:]/w
		return x, y

	def analyze(self):
		x, y = self.run()
		b, a = [1., -1], [1, -1]
		y0 = scipy.signal.lfilter(b, a, x)
		np.clip(y0, -10, 10, y0)
		yd = plt.mlab.detrend_linear(y - y0)
		fig, ax = plt.subplots(3)
		n = len(x) #200
		ax[0].plot(x[:n], "c-.", label="input")
		ax[0].plot(y[:n], "r-", label="output")
		#ax[0].plot(y0[:n], "g--", label="float output")
		#ax[0].plot(yd[:n], "b:", label="quantization noise")
		ax[0].legend(loc="right")
		ax[0].set_xlabel("time (1/fs)")
		ax[0].set_ylabel("signal")
		ax[0].set_xlim(0, n)
		#tx, fx = plt.mlab.psd(x)
		#ty, fy = plt.mlab.psd(y)
		#ax[1].plot(fx, 10*np.log10(ty/tx))
		n = len(x) #//4
		w = np.hanning(n)
		x = (x.reshape(-1, n)*w).sum(0)
		y = (y.reshape(-1, n)*w).sum(0)
		y0 = (y0.reshape(-1, n)*w).sum(0)
		yd = (yd.reshape(-1, n)*w).sum(0)
		t = (np.fft.fft(y)/np.fft.fft(x))[:n/2]
		t0 = (np.fft.fft(y0)/np.fft.fft(x))[:n/2]
		td = (np.fft.fft(yd))[:n/2]
		f = np.fft.fftfreq(n)[:n/2]*2
		fmin = f[1]
		f1 = np.logspace(np.log10(fmin/2), 0., 401)
		_, t1 = scipy.signal.freqz(b, a, worN=f1*np.pi)
		ax[1].plot(f,  20*np.log10(np.abs(t)), "r-")
		#ax[1].plot(f,  20*np.log10(np.abs(t0)), "g--")
		#ax[1].plot(f1, 20*np.log10(np.abs(t1)), "k-")
		#ax[1].plot(f,  20*np.log10(np.abs(td)), "b:")
		#ax[1].set_ylim(-50, 10)
		ax[1].set_xlim(fmin, 1.)
		#ax[1].set_xscale("log")
		ax[1].set_xlabel("frequency (fs/2)")
		ax[1].set_ylabel("magnitude (dB)")
		ax[1].grid(True)
		ax[2].plot(f,  np.rad2deg(np.angle(t)), "r-")
		#ax[2].plot(f,  np.rad2deg(np.angle(t0)), "g--")
		#ax[2].plot(f1, np.rad2deg(np.angle(t1)), "k--")
		##ax[2].plot(f,  np.rad2deg(np.angle(td)), "b:")
		ax[2].set_xlim(fmin, 1.)
		#ax[2].set_xscale("log")
		ax[2].set_xlabel("frequency (fs/2)")
		ax[2].set_ylabel("phase (deg)")
		ax[2].grid(True)
		return fig

def _main():
	kwargs = dict(width=16, samples=1<<14, amplitude=1., pipe=100,
			rate=-2, order=10)
	tb = Transfer(**kwargs)
	print(verilog.convert(tb, ios={tb.dut.x, tb.dut.y}))
	Transfer(**kwargs).analyze()
	plt.show()

if __name__ == "__main__":
	_main()
