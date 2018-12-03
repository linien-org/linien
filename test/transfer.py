# Copyright 2014-2015 Robert Jordens <jordens@gmail.com>
#
# This file is part of redpid.
#
# redpid is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# redpid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with redpid.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import threading

from migen import *
from misoc.interconnect import csr_bus

from iir_coeffs import get_params


class Filter(Module):
    def __init__(self, dut, x, warmup=200, latency=0, interval=1):
        self.submodules.dut = dut
        self.scale = 2**(len(self.dut.x) - 1) - 1

        self.x = (self.scale*np.array(x)).astype(np.int)
        self.y = []
        warmup -= warmup % interval
        self.warmup = warmup
        self.latency = latency
        self.interval = interval

    def tb(self):
        yield from self.dut.writes()
        for i in range(self.warmup):
            yield
        i = 0
        q = []
        for xi in self.x:
            yield self.dut.x.eq(int(xi))
            q.append(i + self.latency + 1)
            for j in range(self.interval):
                if q[0] == i:
                    self.y.append((yield self.dut.y))
                    q.pop(0)
                yield
                i += 1
        while q:
            if q[0] == i:
                self.y.append((yield self.dut.y))
                q.pop(0)
            yield
            i += 1

    def run(self, **kwargs):
        run_simulation(self.dut, self.tb(), **kwargs)
        x = np.array(self.x)/self.scale
        y = np.array(self.y)/self.scale
        return x, y


def get_offset(description, name, busword=8):
    offset = 0
    for c in description:
        if c.name == name:
            return offset
        offset += (c.size + busword - 1)//busword
    raise KeyError("CSR not found: "+name)


class CsrParams(Module):
    def __init__(self, dut, params):
        self.submodules.dut = dut
        self.csrs = dut.get_csrs()
        self.submodules.bank = csr_bus.CSRBank(self.csrs)
        self.params = params
        for k in dir(dut):
            v = getattr(dut, k)
            if isinstance(v, (Signal, int)):
                setattr(self, k, v)

    def writes(self):
        for k in sorted(self.params):
            for c in self.csrs:
                if c.name == k:
                    n = c.size
                    break
            if isinstance(k, str):
                a = get_offset(self.csrs, k)
            else:
                a = k
                n = 1
            v = self.params[k]
            b = (n + 8 - 1)//8
            for i in reversed(range(b)):
                vi = (v >> (i*8)) & 0xff
                yield from self.bank.bus.write(a, vi)
                #vir = (yield from self.bank.bus.read(a))
                #assert vir == vi, (a, vi, vir)
                a += 1


class CsrThread(Module):
    def __init__(self, dut, csrs=None):
        self.queue = []
        if csrs is None:
            csrs = dut.get_csrs()
        self.csrs = csrs
        self.submodules.dut = dut
        self.submodules.bank = csr_bus.CSRBank(csrs)
        self.sim = threading.Thread(target=run_simulation,
                args=(self, self.gen()), kwargs=dict(vcd_name="pid_tb.vcd"))

    def gen(self):
        while True:
            try:
                q = self.queue.pop(0)
                if isinstance(q, threading.Event):
                    q.set()
                elif q is None:
                    break
                elif isinstance(q, int):
                    for i in range(q):
                        print()
                        print('simulation cycle %d of %d' % (i, q),
                              end='\r', flush=True)
                        print()
                        yield
                else:
                    yield from q
            except IndexError:
                yield

    def write(self, addr, value):
        self.queue.append(self.bank.bus.write(addr, value))
        ev = threading.Event()
        self.queue.append(ev)
        ev.wait()

    def read(self, addr):
        t = self.bank.bus.read(addr)
        self.queue.append(t)
        ev = threading.Event()
        self.queue.append(ev)
        ev.wait()

        return t.data


class ResetParams(Module):
    def __init__(self, dut, params):
        self.submodules.dut = dut
        for k in dir(dut):
            v = getattr(dut, k)
            if isinstance(v, (Signal, int)):
                setattr(self, k, v)
        for k, v in params.items():
            getattr(dut, k[0])[int(k[1])].reset = v


class Transfer:
    def __init__(self, b, a, dut, amplitude=.5, samples=1<<12):
        self.b0, self.a0 = b, a = np.array(b), np.array(a)
        dut = self.wrap_dut(b, a, dut)
        np.random.seed(299792458)
        x = np.random.uniform(-amplitude, amplitude, samples)
        self.tb = Filter(dut, x, latency=dut.dut.latency.value, interval=dut.dut.interval.value)

    def wrap_dut(self, b, a, dut):
        raise NotImplementedError

    def analyze(self, **kwargs):
        fig, ax = plt.subplots(3, 1, figsize=(15, 20))
        x, y = self.tb.run(**kwargs)
        y0 = scipy.signal.lfilter(self.b, self.a, x)
        np.clip(y0, -10, 10, y0)
        yd = plt.mlab.detrend_linear(y - y0)
        n = len(x) #200
        ax[0].plot(x[:n], "c-.", label="input")
        ax[0].plot(y[:n], "r-", label="output")
        ax[0].plot(y0[:n], "g--", label="float output")
        ax[0].plot(yd[:n], "b:", label="quantization noise")
        ax[0].legend(loc="right")
        ax[0].set_xlabel("time (1/fs)")
        ax[0].set_ylabel("signal")
        ax[0].set_xlim(0, n)
        #tx, fx = plt.mlab.psd(x)
        #ty, fy = plt.mlab.psd(y)
        #ax[1].plot(fx, 10*np.log10(ty/tx))
        n = len(x)
        w = np.hanning(n)
        x *= w
        y *= w
        y0 *= w
        yd *= w
        xf = np.fft.rfft(x)
        t = np.fft.rfft(y)/xf
        t0 = np.fft.rfft(y0)/xf
        td = np.fft.rfft(yd)/xf
        f = np.fft.fftfreq(n)[:n//2+1]*2
        fmin = f[1]
        f1 = np.logspace(np.log10(fmin/2), 0., 401)
        _, t1 = scipy.signal.freqz(self.b0, self.a0, worN=f1*np.pi)
        _, t2 = scipy.signal.freqz(self.b, self.a, worN=f1*np.pi)
        ax[1].plot(f,  20*np.log10(np.abs(t)), "r-")
        ax[1].plot(f,  20*np.log10(np.abs(t0)), "g--")
        ax[1].plot(f1, 20*np.log10(np.abs(t1)), "k-")
        ax[1].plot(f1, 20*np.log10(np.abs(t2)), "k:")
        ax[1].plot(f,  20*np.log10(np.abs(td)), "b:")
        ax[1].set_ylim(-60, None)
        ax[1].set_xlim(fmin/2, 1.)
        ax[1].set_xscale("log")
        ax[1].set_xlabel("frequency (fs/2)")
        ax[1].set_ylabel("magnitude (dB)")
        ax[1].grid(True)
        ax[2].plot(f,  np.rad2deg(np.angle(t)), "r-")
        ax[2].plot(f,  np.rad2deg(np.angle(t0)), "g--")
        ax[2].plot(f1, np.rad2deg(np.angle(t1)), "k--")
        ax[2].plot(f1, np.rad2deg(np.angle(t2)), "k:")
        #ax[2].plot(f,  np.rad2deg(np.angle(td)), "b:")
        #ax[2].set_ylim()
        ax[2].set_xlim(fmin, 1.)
        ax[2].set_xscale("log")
        ax[2].set_xlabel("frequency (fs/2)")
        ax[2].set_ylabel("phase (deg)")
        ax[2].grid(True)
        return fig


class ResetTransfer(Transfer):
    def wrap_dut(self, b, a, dut):
        self.b, self.a, params = get_params(b, a, shift=dut.shift.value,
                width=len(dut.a[1]))
        dut = ResetParams(dut, params)
        return dut


class CsrTransfer(Transfer):
    def wrap_dut(self, b, a, dut):
        self.b, self.a, params = get_params(b, a, shift=dut.shift.value,
                width=len(dut.c["a1"]))
        dut = CsrParams(dut, params)
        return dut
