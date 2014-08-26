import subprocess

from csrmap import csrmap
import iir_coeffs


class PitayaCSR:
    map = csrmap

    def set(self, name, value):
        addr, nr, wr = self.map[name]
        assert wr, name
        ma = 1<<nr*8
        val = value & (ma - 1)
        assert value >= -ma/2 or value < ma, (value, val, ma)
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
        shift = self.get(prefix + "_shift")
        width = self.get(prefix + "_width")
        b, a, params = iir_coeffs.get_params(b, a, shift, width)
        print(params)
        for k in sorted(params):
            self.set(prefix + "_" + k, params[k])


class PitayaReal(PitayaCSR):
    mon = "/opt/bin/monitor"

    def __init__(self, url="root@192.168.3.42"):
        self.url = url

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


if __name__ == "__main__":
    p = PitayaReal()
    assert p.get("pid_version") == 1
    da = 0x12345
    p.set("deltasigma_data0", da)
    assert p.get("deltasigma_data0") == da

    new = """
        in_a_tap=0
        iomux_mux_a=1
        out_a_iir_a_z0=0
        out_a_iir_a_a1=0
        out_a_iir_a_b0=0
        out_a_iir_a_b1=0
        out_a_tap=1        
        out_a_mode=0
        out_a_relock_mode=4
        out_a_relock_step=0
        out_a_limit_min=-8192
        out_a_limit_max=8191
        out_a_sweep_mode=8
        out_a_sweep_step=0
        out_a_mod_amp=0

        in_b_tap=0
        iomux_mux_b=2
        out_b_iir_a_z0=0
        out_b_iir_a_a1=0
        out_b_iir_a_b0=0
        out_b_iir_a_b1=0
        out_b_iir_a_mode=3
        out_b_tap=1
        out_b_mode=0
        out_b_relock_mode=4
        out_b_relock_step=0
        out_b_limit_min=0
        out_b_limit_max=8000
        out_b_sweep_mode=0
        out_b_sweep_step=1
        out_b_sweep_min=4000
        out_b_sweep_max=4000
        out_b_mod_amp=0
        out_b_mod_freq=10000
    """
    for l in new.splitlines():
        l = l.strip()
        if not l:
            continue
        k, v = l.strip().split("=")
        p.set("pid_" + k, int(v))
    
    b, a = iir_coeffs.make_filter("P", k=-1)
    #b, a = iir_coeffs.make_filter("I", k=.01, f=1e-2)
    #b, a = iir_coeffs.make_filter("PI", f=2e-3, g=1e20, k=-.1)
    p.set_iir("pid_out_a_iir_a", b, a)

    settings = {}
    for n in sorted(p.map):
        settings[n] = v = p.get(n)
        print(n, hex(v))


