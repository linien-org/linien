# Robert Jordens <jordens@gmail.com> 2014

from migen.fhdl.std import *

class RedPid(Module):
    def __init__(self, platform):
        exp = platform.request("exp")
        #xadc = platform.request("xadc")
        dac = platform.request("dac")
        adc0 = platform.request("adc", 0)
        adc1 = platform.request("adc", 1)
        adc_clk = platform.request("adc_clk")
        self.comb += [
                exp.raw_bits().eq(0),
                #xadc.raw_bits().eq(0),
                dac.raw_bits().eq(0),
                adc0.eq(0),
                adc1.eq(0),
                adc_clk.eq(0),
        ]
