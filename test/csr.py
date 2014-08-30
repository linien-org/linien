import subprocess

import csrmap
from iir_coeffs import make_filter, get_params


class PitayaCSR:
    map = csrmap.csr

    def set(self, name, value):
        addr, nr, wr = self.map[name]
        assert wr, name
        ma = 1<<nr
        val = value & (ma - 1)
        assert value >= -ma/2 and value < ma, (value, val, ma)
        b = (nr + 8 - 1)//8
        for i in range(b):
            v = (val >> (8*(b - i - 1))) & 0xff
            self.set_one(addr + i*4, v)

    def get(self, name):
        addr, nr, wr = self.map[name]
        v = 0
        b = (nr + 8 - 1)//8
        for i in range(b):
            v |= self.get_one(addr + i*4) << 8*(b - i - 1)
        return v

    def set_iir(self, prefix, b, a, z=0):
        shift = self.get(prefix + "_shift") or 16
        width = self.get(prefix + "_width") or 25
        b, a, params = get_params(b, a, shift, width)
        print(params)
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
        self.url = url

    def run(self):
        pass

    def cmd(self, *cmd):
        p = subprocess.Popen(("ssh", self.url) + cmd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        o, e = p.communicate()
        if e:
            raise ValueError((cmd, o, e))
        return o

    def set_one(self, addr, value):
        cmd = "0x{:08x} 0x{:02x}".format(addr, value)
        self.cmd(self.mon, *cmd.split())

    def get_one(self, addr):
        cmd = "0x{:08x}".format(addr)
        ret = self.cmd(self.mon, *cmd.split())
        return int(ret, 16)


class PitayaTB(PitayaCSR):
    def __init__(self):
        from transfer import Filter, CsrParams
        from gateware.pid import Pid
        self.params = {}
        p = Pid()
        p.x = p.in_a.adc
        p.y = p.out_a.dac
        p = CsrParams(p, self.params)
        self.tb = Filter(p, [0, 0, 0, 0])

    def run(self):
        return self.tb.run(vcd_name="pid_tb.vcd")

    def set_one(self, addr, value):
        self.params[(addr - 0x40300000)//4] = value

    def get_one(self, addr):
        return 0


if __name__ == "__main__":
    p = PitayaReal()
    #p = PitayaTB()
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
        fast_a_x_tap=0,
        fast_a_x_zero=0,
        fast_a_dx_sel=p.signal("zero"),
        fast_a_y_tap=1,
        fast_a_rx_sel=p.signal("fast_a_x"),
        fast_a_y_hold_en=p.states("fast_a_unlocked"),
        fast_a_y_clear_en=p.states(), #"fast_a_y_railed"),
        fast_a_relock_run=1,
        fast_a_relock_en=p.states(),
        fast_a_relock_step=200000,
        fast_a_relock_min=-4000,
        fast_a_relock_max=4000,
        fast_a_sweep_run=0,
        fast_a_sweep_step=100000,
        fast_a_sweep_min=-4000,
        fast_a_sweep_max=4000,
        fast_a_mod_amp=0,
        fast_a_mod_freq=10000,
        fast_a_dy_sel=p.signal("scopegen_dac_a"),
        noise_bits=23,
        fast_a_y_limit_min=-8192,
        fast_a_y_limit_max=8191,

        scopegen_adc_a_sel=p.signal("fast_a_x"),
        scopegen_adc_b_sel=p.signal("fast_a_y"),

        gpio_p_oe=0,
        gpio_n_oe=0xff,
        gpio_n_do0_en=p.states("fast_a_x_sat"),
        gpio_n_do1_en=p.states("fast_a_y_sat"),
        gpio_n_do2_en=p.states("fast_a_y_railed"),
        gpio_n_do3_en=p.states("fast_a_unlocked"),
        gpio_n_do4_en=p.states("fast_b_x_sat"),
        gpio_n_do5_en=p.states("fast_b_y_sat"),
        gpio_n_do6_en=p.states("fast_b_y_railed"),
        gpio_n_do7_en=p.states("fast_b_unlocked"),
    )
    for k, v in sorted(new.items()):
        p.set(k, int(v))
    
    # 182ns latency, 23 cycles (6 adc, 1 in, 1 comp, 1 in_a_y, 1 iir_x,
    # 1 iir_b0, 1 iir_y, 1 out_a_y, 1 out_a_lim_x, 1 out_dac, 1 comp, 1 oddr, 1
    # dac) = 18 + analog filter
    #b, a = make_filter("P", k=-.1)
    n = "fast_a_iir_c"
    #p.set_iir(n, *make_filter("P", k=-.8, f=1))
    #p.set_iir(n, *make_filter("I", k=4e-5, f=1))
    #p.set_iir("fast_a_iir_c", *make_filter("P", k=-.5, f=1))
    #p.set_iir("fast_a_iir_c", *make_filter("P", k=1, f=1))
    p.set_iir("fast_a_iir_d", *make_filter("P", k=1, f=1))
    #p.set_iir("fast_a_iir_e", *make_filter("PI", k=-.01*.1, f=.01))
    p.set_iir("fast_a_iir_e", *make_filter("I", k=1e-6, f=1))
    #p.set_iir(n, *make_filter("PI", f=.2, k=-.2))
    p.set_iir(n, *make_filter("I", k=-1e-3, f=1))

    p.run()

    settings = {}
    for n in sorted(p.map):
        settings[n] = v = p.get(n)
        print(n, hex(v))


