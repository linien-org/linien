import subprocess

from csrmap import csrmap
from iir_coeffs import make_filter, get_params


class PitayaCSR:
    map = csrmap

    def set(self, name, value):
        addr, nr, wr = self.map[name]
        assert wr, name
        ma = 1<<nr*8
        val = value & (ma - 1)
        assert value >= -ma/2 and value < ma, (value, val, ma)
        for i in range(nr):
            v = (val >> (8*(nr - i - 1))) & 0xff
            self.set_one(addr + i*4, v)

    def get(self, name):
        addr, nr, wr = self.map[name]
        v = 0
        for i in range(nr):
            v |= self.get_one(addr + i*4) << 8*(nr - i -1)
        return v

    def set_iir(self, prefix, b, a):
        shift = self.get(prefix + "_shift") or 16
        width = self.get(prefix + "_width") or 25
        b, a, params = get_params(b, a, shift, width)
        print(params)
        for k in sorted(params):
            self.set(prefix + "_" + k, params[k])


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
    p.set("slow_deltasigma_data0", da)
    p.set("slow_led", 0)
    #assert p.get("deltasigma_data0") == da
    #print(hex(p.get("slow_dna_dna")))
    #assert p.get("slow_dna_dna") & 0x7f == 0b1000001
    print("temp", p.get("slow_xadc_temp")*503.975/0xfff-273.15)
    for u, ns in [(3./0xfff, "pint paux bram int aux ddr"),
            (1./0xfff*(30 + 4.99)/4.99, "a b c d"),
            (1./0xfff*(56 + 4.99)/4.99, "v")]:
        for n in ns.split():
            v = p.get("slow_xadc_{}".format(n))
            if v & 0x800 and n in "abcd":
                v = 0 #v - 0x1000
            print(n, u*v)

    new = dict(
        in_a_iir_a_b0=0,
        in_a_tap=0,
        iomux_out_a_x=1,
        out_a_iir_a_z0=0,
        out_a_iir_a_a1=0,
        out_a_iir_a_b0=0,
        out_a_iir_a_b1=0,
        out_a_tap=1,
        iomux_out_a_relock=0, # limit
        iomux_out_a_hold=1<<3, # relock
        iomux_out_a_clear=1<<4, # limit
        iomux_out_a_relock_x=0, # in a
        out_a_relock_step=500000,
        out_a_relock_min=-16384,
        out_a_relock_max=16383,
        out_a_limit_min=-8192,
        out_a_limit_max=8191,
        out_a_sweep_step=0,
        out_a_mod_amp=0,

        in_b_tap=0,
        iomux_out_b_x=2,
        out_b_tap=1,
        out_b_relock_step=0,
        out_b_sweep_step=0,
    )
    for k, v in new.items():
        p.set("pid_" + k, int(v))
    
    # 182ns latency, 23 cycles (6 adc, 1 in, 1 comp, 1 in_a_y, 1 iir_x,
    # 1 iir_b0, 1 iir_y, 1 out_a_y, 1 out_a_lim_x, 1 out_dac, 1 comp, 1 oddr, 1
    # dac) = 18 + analog filter
    #b, a = make_filter("P", k=-.1)
    #p.set_iir("pid_out_a_iir_a", *make_filter("P", k=-.8, f=1))
    #p.set_iir("pid_out_a_iir_a", *make_filter("I", k=4e-5, f=1))
    #p.set_iir("pid_out_a_iir_a", *make_filter("I", k=-.01, f=1))
    p.set_iir("pid_out_a_iir_a", *make_filter("PI", f=.6, k=-.05))
    #p.set_iir("pid_out_a_iir_a", *make_filter("PI", f=.5, k=-.05))

    p.run()

    settings = {}
    for n in sorted(p.map):
        settings[n] = v = p.get(n)
        print(n, hex(v))


