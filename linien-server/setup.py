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

from setuptools import find_packages, setup

version = "0.6.0rc3"

setup(
    name="linien-server",
    version=version,
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    maintainer="Bastian Leykauf",
    maintainer_email="leykauf@physik.hu-berlin.de",
    description="Server components of the Linien spectroscopy lock application.",
    long_description="Have a look at the [project repository](https://github.com/linien-org/linien) for installation instructions.",  # noqa: E501
    long_description_content_type="text/markdown",
    url="https://github.com/linien-org/linien",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["linien-server=linien_server.server:run_server"]},
    python_requires=">=3.5",
    install_requires=[
        "click>=7.1.2",
        "cma>=3.0.3",
        "myhdl>=0.11",
        "pylpsd>=0.1.4",
        # "pyrp3>=1.1.0", # FIXME: Enable once pyrp3 is on PyPI
        "rpyc>=4.0,<5.0",
        "linien-common=={}".format(version),
    ],
    scripts=[
        "linien_server/linien_start_server.sh",
        "linien_server/linien_stop_server.sh",
        "linien_server/linien_install_requirements.sh",
    ],
    package_data={
        "": [
            "linien.bin",
            "linien_start_server.sh",
            "linien_stop_server.sh",
            "linien_install_requirements.sh",
        ]
    },
)
