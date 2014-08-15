# Robert Jordens <jordens@gmail.com> 2014

from gateware.platform import Platform
from gateware.redpid import RedPid


if __name__ == "__main__":
    platform = Platform()
    redpid = RedPid(platform)
    platform.add_source_dir("verilog")
    platform.build_cmdline(redpid, build_name="redpid")
