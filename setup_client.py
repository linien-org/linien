import setuptools

import linien

assert linien.__version__ != "dev"

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements_client", "r") as fh:
    requirements = fh.read().split(" ")

setuptools.setup(
    name="linien-python-client",
    version=linien.__version__,
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    description="Python client for linien spectroscopy lock",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hermitdemschoenenleben/linien",
    # IMPORTANT: any changes have to be made in setup_client_and_gui.py
    # of flathub repo as well
    packages=["linien", "linien.client"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    install_requires=[requirements],
    package_data={
        # IMPORTANT: any changes have to be made in pyinstaller.spec, too
        # (for the standalone installer)
        # IMPORTANT: any changes have to be made in setup_client_and_gui.py
        # of flathub repo as well
        "": ["VERSION"]
    },
)
