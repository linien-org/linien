import os

name = "linien"

from plumbum import colors

version_fn = os.path.join(
    *list(os.path.split(os.path.abspath(__file__))[:-1]) + ["VERSION"]
)

try:
    with open(version_fn, "r") as fh:
        __version__ = fh.read().strip()
        assert __version__ == "dev" or len(__version__.split(".")) == 3, (
            "invalid version number! Either has to be dev or something like " "1.0.1"
        )
except FileNotFoundError:
    print(
        colors.red | "Unable to read VERSION file. Create a file called "
        "VERSION in the checked_out_repo/linien folder. "
        'The content should be either "dev" for development or a '
        "version number if you want to release a new production version. "
        "Consult README for more details."
    )
    raise
