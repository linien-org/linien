# Robert Jordens <jordens@gmail.com> 2014

from gateware.platform import Platform
from gateware.redpid import RedPid


def _main():
    platform = Platform()
    pdq = RedPid(platform)
    platform.build_cmdline(pdq, build_name="redpid")


if __name__ == "__main__":
    _main()
