from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution("linien-server").version
except DistributionNotFound:
    # package is not installed
    pass
