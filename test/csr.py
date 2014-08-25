import subprocess

from csrmap import csrmap
import iir_coeffs

class PitayaCSR:
    map = csrmap
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

    def set(self, name, value):
        addr, nr, wr = self.map[name]
        assert wr, name
        ma = 1<<nr*8
        val = value & (ma - 1)
        assert value >= -ma/2 or value < ma, (value, val, ma)
        for i in range(nr):
            v = (val >> (8*(nr - i - 1))) & 0xff
            cmd = "0x{:08x} 0x{:02x}".format(addr + i*4, v)
            self.cmd(self.mon, *cmd.split())

    def get(self, name):
        addr, nr, wr = self.map[name]
        v = 0
        for i in range(nr):
            cmd = "0x{:08x}".format(addr + i*4)
            ret = self.cmd(self.mon, *cmd.split())
            v |= int(ret, 16) << 8*(nr - i -1)
        return v

    def set_iir(self, prefix, b, a):
        shift = self.get(prefix + "_shift")
        #width = self.get(prefix + "_width")
        width = 25
        b, a, params = iir_coeffs.get_params(b, a, shift, width)
        print(params)
        for k in sorted(params):
            self.set(prefix + "_" + k, params[k])


if __name__ == "__main__":
    p = PitayaCSR()
    assert p.get("pid_version") == 1
    da = 0x12345
    p.set("deltasigma_data0", da)
    assert p.get("deltasigma_data0") == da

    new = """
        iomux_mux_a=0
        iomux_mux_b=1
        in_a_tap=0
        in_b_tap=0
        out_b_tap=1
        out_b_mode=0
        out_a_tap=0
        out_a_mode=0
    """
    for l in new.splitlines():
        l = l.strip()
        if not l:
            continue
        k, v = l.strip().split("=")
        p.set("pid_" + k, int(v))
    
    b, a = iir_coeffs.make_filter("PI",
            f=2e-5, g=1e20, k=-.99)
    p.set_iir("pid_out_b_iir_a", b, a)

    settings = {}
    for n in sorted(p.map):
        settings[n] = v = p.get(n)
        print(n, hex(v))


