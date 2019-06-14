import os

name = "linien"

version_fn = os.path.join(
    *list(os.path.split(os.path.abspath(__file__))[:-1]) + ['VERSION']
)

with open(version_fn, 'r') as fh:
    __version__ = fh.read().strip()