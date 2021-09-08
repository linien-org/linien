import setuptools

import linien

assert linien.__version__ != "dev"

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="linien",
    version=linien.__version__,
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    description="Spectroscopy lock application using RedPitaya",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://hermitdemschoenenleben.github.io/linien/",
    # IMPORTANT: any changes have to be made in setup_client_and_gui.py
    # of flathub repo as well
    packages=["linien", "linien.gui", "linien.gui.ui"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["linien=linien.gui.app:run_application"]},
    install_requires=[
        "click>=7.1.2",
        "numpy>=1.19.1",
        "paramiko>=2.7.1",
        "plumbum>=1.6.9",
        "pyqtgraph>=0.10.0",
        "PyQt5>=5.12.0",
        "rpyc>=4.0,<5.0",
        "scipy>=1.4.1",
        "superqt>=0.2.3",
        "linien-python-client==" + linien.__version__,
    ],
    package_data={
        # IMPORTANT: any changes have to be made in pyinstaller.spec, too
        # (for the standalone installer)
        # IMPORTANT: any changes have to be made in setup_client_and_gui.py
        # of flathub repo as well
        "": ["*.ui", "VERSION", "*.ico"]
    },
)
