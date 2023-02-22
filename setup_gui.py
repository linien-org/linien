# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

import setuptools

import linien

assert linien.__version__ != "dev"

long_description = """

---
**DEPRICATION NOTE**

This package has been moved to [linien-gui](https://pypi.org/project/linien-gui/) as of Linien v0.6.0. Please have a look at the [project repository](https://github.com/linien-org/linien) for up to date installation instructions.

---

"""
with open("README.md", "r") as fh:
    long_description += fh.read()

setuptools.setup(
    name="linien",
    version=linien.__version__,
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    maintainer="Bastian Leykauf",
    maintainer_email="leykauf@physik.hu-berlin.de",
    description="Spectroscopy lock application using RedPitaya",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/linien-org/linien",
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
        "paramiko>=2.10.1",
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
