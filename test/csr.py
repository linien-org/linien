import subprocess

import csrmap
from iir_coeffs import make_filter, get_params


class PitayaCSR:
    map = csrmap.csr
    offset = 0x40300000

    def set(self, name, value):
        map, addr, nr, wr = self.map[name]
        assert wr, name
        ma = 1<<nr
        val = value & (ma - 1)
        assert value == val or ma + value == val, (value, val, ma)
        b = (nr + 8 - 1)//8
        for i in range(b):
            v = (val >> (8*(b - i - 1))) & 0xff
            self.set_one(self.offset + (map << 11) + ((addr + i)<<2), v)

    def get(self, name):
        map, addr, nr, wr = self.map[name]
        v = 0
        b = (nr + 8 - 1)//8
        for i in range(b):
            v |= self.get_one(self.offset + (map << 11) + ((addr + i)<<2)
                    ) << 8*(b - i - 1)
        return v

    def set_iir(self, prefix, b, a, z=0):
        shift = self.get(prefix + "_shift") or 16
        width = self.get(prefix + "_width") or 18
        interval = self.get(prefix + "_interval") or 1
        b, a, params = get_params(b, a, shift, width, interval)
        print(params, interval)
        for k in sorted(params):
            self.set(prefix + "_" + k, params[k])
        self.set(prefix + "_z0", z)
        for i in range(len(b), 3):
            n = prefix + "_b%i" % i
            if n in self.map:
                self.set(n, 0)
                self.set(prefix + "_a%i" % i, 0)

    def signal(self, name):
        return csrmap.signals.index(name)

    def states(self, *names):
        return sum(1<<csrmap.states.index(name) for name in names)


class PitayaReal(PitayaCSR):
    mon = "/opt/bin/monitor"

    def __init__(self, url="root@192.168.3.42"):
        self.p = subprocess.Popen(("ssh", url, self.mon, "-"),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

    def start(self):
        pass

    def stop(self, n=None):
        pass

    def set_one(self, addr, value):
        cmd = "0x{:08x} w 0x{:02x}\n\n".format(addr, value)
        self.p.stdin.write(cmd.encode("ascii"))
        self.p.stdin.flush()

    def get_one(self, addr):
        cmd = "0x{:08x} w\n\n".format(addr)
        self.p.stdin.write(cmd.encode("ascii"))
        self.p.stdin.flush()
        ret = self.p.stdout.readline().decode("ascii")
        return int(ret, 16)


class PitayaTB(PitayaCSR):
    def __init__(self, x=None):
        from transfer import Filter, CsrThread
        from gateware.pid import FastChain
        import numpy as np
        p = FastChain(14, 25, 18)
        p.x = p.adc
        p.y = p.dac
        if x is None:
            x = np.random.uniform(-.8, .8, 1<<12)
        self.io = Filter(p, x)
        self.csr = CsrThread(self.io, p.get_csrs())
        self.offset = 0x40300000

    def start(self):
        self.csr.sim.start()

    def stop(self, n=0):
        self.csr.queue.append(n)
        self.csr.queue.append(None)
        self.csr.sim.join()

    def set_one(self, addr, value):
        addr -= self.offset
        return self.csr.write(addr//4, value)

    def get_one(self, addr):
        addr -= self.offset
        return self.csr.read(addr//4)


if __name__ == "__main__":
    p = PitayaReal()
    #p = PitayaTB()
    p.start()
    #assert p.get("pid_version") == 1
    da = 0x2345
    #assert p.get("deltasigma_data0") == da
    #print(hex(p.get("slow_dna_dna")))
    #assert p.get("slow_dna_dna") & 0x7f == 0b1000001
    print("temp", p.get("xadc_temp")*503.975/0xfff-273.15)
    for u, ns in [(3./0xfff, "pint paux bram int aux ddr"),
            (1./0xfff*(30 + 4.99)/4.99, "a b c d"),
            (1./0xfff*(56 + 4.99)/4.99, "v")]:
        for n in ns.split():
            v = p.get("xadc_{}".format(n))
            if v & 0x800 and n in "abcd":
                v = 0 #v - 0x1000
            print(n, u*v)

    new = dict(
        fast_a_x_tap=3,
        fast_a_demod_phase=0x0000,
        fast_a_x_clear_en=0, #p.states("fast_a_x_sat"),
        fast_a_break=0,
        fast_a_dx_sel=p.signal("zero"),
        fast_a_y_tap=3,
        fast_a_rx_sel=p.signal("fast_a_x"),
        fast_a_y_hold_en=p.states("fast_a_unlocked"),
        fast_a_y_clear_en=p.states("fast_a_y_railed"),
        fast_a_relock_run=0,
        fast_a_relock_en=p.states("fast_a_y_sat"),
        fast_a_relock_step=20000,
        fast_a_relock_min=-8000,
        fast_a_relock_max=8000,
        fast_a_sweep_run=0,
        fast_a_sweep_step=100000,
        fast_a_sweep_min=-4000,
        fast_a_sweep_max=4000,
        fast_a_mod_amp=0x0004,
        fast_a_mod_freq=0x000023450,
        fast_a_dy_sel=p.signal("scopegen_dac_a"),
        fast_a_y_limit_min=-8192,
        fast_a_y_limit_max=8191,

        fast_b_x_tap=0,
        fast_b_break=1,
        fast_b_dx_sel=p.signal("noise_y"),
        fast_b_y_tap=3,
        fast_b_y_clear_en=p.states("fast_b_y_railed"),
        fast_b_mod_amp=0*0x2000,
        fast_b_mod_freq=0*0x00000100,
        fast_b_dy_sel=p.signal("zero"),

        slow_a_break=0,
        slow_a_dx_sel=p.signal("scopegen_dac_a"),
        slow_a_clear_en=p.states("slow_a_sat"),
        slow_a_y_limit_min=0,

        noise_bits=25,
        scopegen_adc_a_sel=p.signal("fast_b_x"),
        scopegen_adc_b_sel=p.signal("fast_b_y"),

        gpio_p_oe=0,
        gpio_n_oe=0xff,
        gpio_n_do0_en=p.states("fast_a_x_sat"),
        gpio_n_do1_en=p.states("fast_a_y_sat"),
        gpio_n_do2_en=p.states("fast_a_y_railed"),
        gpio_n_do3_en=p.states("fast_a_unlocked"),
        gpio_n_do4_en=p.states("slow_a_sat"),
        gpio_n_do5_en=p.states("slow_a_railed"),
    )
    for k, v in sorted(new.items()):
        p.set(k, int(v))
    
    # 182ns latency, 23 cycles (6 adc, 1 in, 1 comp, 1 in_a_y, 1 iir_x,
    # 1 iir_b0, 1 iir_y, 1 out_a_y, 1 out_a_lim_x, 1 out_dac, 1 comp, 1 oddr, 1
    # dac) = 18 + analog filter
    #b, a = make_filter("P", k=-.1)
    p.set_iir("fast_a_iir_a", *make_filter("HP", k=2, f=1e-5))
    #p.set_iir("fast_a_iir_b", *make_filter("LP", k=2000, f=5e-8))
    #p.set_iir("fast_a_iir_b", *make_filter("LP2", k=1000, f=5e-4, g=1e6, q=.5))
    p.set_iir("fast_a_iir_b", *make_filter("LP", k=5000, f=1e-7))
    n = "fast_a_iir_c"
    p.set_iir("fast_a_iir_c", *make_filter("P", k=1., f=1))
    p.set_iir("fast_a_iir_d", *make_filter("P", k=1., f=1))
    #p.set_iir("fast_a_iir_e", *make_filter("I", k=1, f=2e-7))
    p.set_iir("fast_a_iir_e", *make_filter("LP", k=1, f=1e-7))
    #p.set_iir("fast_a_iir_e", *make_filter("IHO", k=-1e-3, f=1e-4, g=10, q=2.5))
    #p.set_iir(n, *make_filter("P", k=-1.047, f=1))
    #p.set_iir(n, *make_filter("I", k=4e-5, f=1))
    #p.set_iir("fast_a_iir_c", *make_filter("P", k=-.5, f=1))
    #p.set_iir("fast_a_iir_c", *make_filter("P", k=1, f=1))
    #p.set_iir("fast_a_iir_d", *make_filter("P", k=1, f=1))
    #p.set_iir("fast_a_iir_e", *make_filter("PI", k=-.01*.1, f=.01))
    #p.set_iir("fast_a_iir_e", *make_filter("PI", f=1e-3, k=.00001), z=1<<31)
    #p.set_iir("fast_a_iir_e", *make_filter("PI", f=5e-6, k=-1e-2), z=0)
    #p.set_iir("fast_a_iir_e", *make_filter("I", f=3e-7, k=-1), z=0)
    #p.set_iir(n, *make_filter("PI", f=.2, k=-.2))
    #p.set_iir(n, *make_filter("PI", f=2e-1, k=1e-4))
    #p.set_iir(n, *make_filter("PI", f=2e-1, k=-1e-3))
    #p.set_iir(n, *make_filter("LP", f=1e-4, k=1.))
    #p.set_iir(n, *make_filter("I", k=4e-5, f=1))
    p.set_iir("fast_b_iir_c", *make_filter("LP", k=10, f=2e-5))
    #p.set_iir("fast_b_iir_d", *make_filter("P", k=.1, f=1))
    p.set_iir("fast_b_iir_d", *make_filter("LP", k=1, f=2e-5))
    #p.set_iir("fast_b_iir_e", *make_filter("LP", k=500, f=1e-7), z=-3000)
    #p.set_iir("fast_b_iir_e", *make_filter("NOTCH", k=1, f=2e-4, q=.707))
    #p.set_iir("fast_b_iir_e", *make_filter("NOTCH", k=.99, f=1e-4, g=10., q=.5))
    p.set_iir("fast_b_iir_e", *make_filter("LP2", k=1.99, f=1.5e-4, g=10., q=40.))
    #p.set_iir("fast_b_iir_e", *make_filter("LP", k=.1, f=1e-3, q=.5))
    #p.set_iir("fast_b_iir_e", *make_filter("LP", k=1000, f=1e-7, q=1.5))
    #p.set_iir("fast_b_iir_e", *make_filter("LP2", k=1, f=5e-4, q=3))
    #p.set_iir("fast_b_iir_e", *make_filter("IHO", k=.01, f=2e-3, q=10, g=10))
    #p.set_iir("fast_b_iir_e", *make_filter("NOTCH", k=1., f=5e-4, q=2))
    #p.set_iir("fast_b_iir_e", *make_filter("LP2", k=10, f=1.5e-4, q=1.5))
    #p.set_iir("slow_a_iir", *make_filter("PI", k=-1e-3, f=1e-5), z=-0x10000)
    p.set_iir("slow_a_iir", *make_filter("PI", k=-.01, f=1e-4), z=0)
    #p.set_iir("slow_a_iir", *make_filter("P", k=1, f=1.), z=0)

    settings = {}
    for n in sorted(p.map):
        settings[n] = v = p.get(n)
        print(n, hex(v))

    p.stop(5000)

    import matplotlib.pyplot as plt
    #plt.plot(p.io.y)
    #plt.show()
