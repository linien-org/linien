# (C) Roberr Jordens <jordens@gmail.com> 2014, 2015

from math import log, ceil

from migen.fhdl.std import *
from migen.genlib.misc import optree


class CIC(Module):
	def __init__(self, width=18, rate=-4, order=4, pipe=1):
		self.width = width
		assert abs(rate) > 1
		self.rate = rate
		self.order = order
		self.pipe = pipe

		self.x = Signal((width, True))
		self.y = Signal((width, True))
		self.stb = stb = Signal()
		
		##

		bitgain = order*ceil(log(abs(rate))/log(2))
		self.latency = 0

		x = Signal((width + bitgain, True))
		self.comb += x.eq(Cat(self.x, Replicate(self.x[-1], bitgain)))
		if rate > 0:
			x = self._pipe(self._combs(x))
			y = self._interpolate(x)
			y = self._pipe(self._integrators(y))
		else:
			x = self._pipe(self._integrators(x))
			y = self._decimate(x)
			y = self._pipe(self._combs(y))
		self.comb += self.y.eq(y>>bitgain)

	def _delay(self, x, stb=None):
		y = Signal((flen(x), True))
		if stb is None:
			self.sync += y.eq(x)
		else:
			self.sync += If(stb, y.eq(x))
		return y

	def _pipe(self, gen):
		x = None
		i = 0
		while True:
			try:
				x = gen.send(x)
			except StopIteration:
				return x
			i += 1
			if i >= self.pipe:
				x = self._delay(x)
				self.latency += 1
				i = 0

	def _combs(self, x):
		for i in range(self.order):
			y = x
			for j in range(abs(self.rate) - 1):
				y = self._delay(y, self.stb)
			x0, x = x, Signal((flen(x), True))
			self.comb += x.eq(x0 - y)
			x = yield x

	def _interpolate(self, x):
		y = Signal((flen(x), True))
		self.comb += If(self.stb, y.eq(x)).Else(y.eq(0))
		return y

	def _decimate(self, x):
		y = Signal((flen(x), True))
		y0 = Signal((flen(x), True))
		self.sync += y0.eq(y)
		self.comb += If(self.stb, y.eq(x)).Else(y.eq(y0))
		return y

	def _integrators(self, x):
		for i in range(self.order):
			x0, x = x, Signal((flen(x), True))
			self.comb += x.eq(x0 + self._delay(x))
			x = yield x
