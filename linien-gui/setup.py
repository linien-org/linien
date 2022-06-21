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

import re

from setuptools import find_packages, setup

version_file = "linien_client/_version.py"
with open(version_file, "rt") as f:
    verstrline = f.read()
mo = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", verstrline, re.M)
verstr = mo.group(1)

setup(
    name="linien-gui",
    version=verstr,
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    maintainer="Bastian Leykauf",
    maintainer_email="leykauf@physik.hu-berlin.de",
    description="Spectroscopy lock application using RedPitaya",
    long_description="Have a look at the 'linien' package for installation instructions.",  # noqa: E501
    long_description_content_type="text/x-rst",
    url="https://github.com/linien-org/linien",
    packages=find_packages(),
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
        "linien_client=={}".format(verstr),
    ],
    package_data={
        # IMPORTANT: any changes have to be made in pyinstaller.spec, too
        # (for the standalone installer)
        "": ["*.ui", "*.ico"]
    },
)
