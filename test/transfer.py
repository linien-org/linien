import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

from migen.fhdl.std import *
from migen.sim.generic import run_simulation, StopSimulation
from migen.bus.csr import Initiator
from migen.bank.csrgen import get_offset, Bank
from migen.bus.transactions import TWrite

from iir_coeffs import get_params


class Filter(Module):
    def __init__(self, dut, amplitude, samples, warmup=200):
        self.submodules.dut = dut
        self.scale = 2**(flen(self.dut.x) - 1) - 1

        if isinstance(amplitude, float):
            np.random.seed(299792458)
            x = np.random.uniform(-amplitude*self.scale, amplitude*self.scale,
                samples).astype(np.int)
        else:
            x = (amplitude*self.scale).astype(np.int)
        self.x = x
        self.xgen = iter(x)
        self.ygen = []
        self.y = []
        warmup -= warmup % self.dut.interval
        self.warmup = warmup

    def do_simulation(self, selfp):
        c = selfp.simulator.cycle_counter - self.warmup
        if c < 0:
            return
        if len(self.y) == len(self.x):
            raise StopSimulation
        try:
            if c % self.dut.interval == 0:
                selfp.dut.x = next(self.xgen)
                self.ygen.append(c + 1 + self.dut.latency)
        except StopIteration:
            pass
        try:
            if c == self.ygen[0]:
                self.ygen.pop(0)
                self.y.append(selfp.dut.y)
        except IndexError:
            pass

    def run(self, **kwargs):
        run_simulation(self, **kwargs)
        x = np.array(self.x)/self.scale
        y = np.array(self.y)/self.scale
        return x, y


class CsrParams(Module):
    def __init__(self, dut, params):
        self.submodules.dut = dut
        self.desc = dut.get_csrs()
        self.submodules.bank = Bank(self.desc)
        self.submodules.init = Initiator(self.writes(),
                self.bank.bus)
        self.params = params
        for k in dir(dut):
            v = getattr(dut, k)
            if isinstance(v, (Signal, int)):
                setattr(self, k, v)

    def writes(self):
        for k in sorted(self.params):
            for c in self.desc:
                if c.name == k:
                    n = c.size
                    break
            a = get_offset(self.desc, k)
            v = self.params[k]
            b = (n + 8 - 1)//8
            for i in reversed(range(b)):
                vi = (v >> (i*8)) & 0xff
                yield TWrite(a, vi)
                a += 1


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
        self.tb = Filter(dut, amplitude, samples)

    def wrap_dut(self, b, a, dut):
        raise NotImplementedError

    def analyze(self):
        fig, ax = plt.subplots(3, 1, figsize=(15, 20))
        x, y = self.tb.run()
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
        self.b, self.a, params = get_params(b, a, shift=dut.shift.reset,
                width=flen(dut.a[1]))
        dut = ResetParams(dut, params)
        return dut


class CsrTransfer(Transfer):
    def wrap_dut(self, b, a, dut):
        self.b, self.a, params = get_params(b, a, shift=dut.r_shift.status.reset,
                width=flen(dut.c["a1"]))
        dut = CsrParams(dut, params)
        return dut
