# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2022-2023 Bastian Leykauf <leykauf@physik.hu-berlin.de>
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

setup(
    name="linien-server",
    version="1.0.2",
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
        "certifi==2021.10.8;python_version<'3.10'",  # pinned because of bug in pip 9.0.1, see #339 # noqa: E501
        "click>=7.1.2",
        "cma>=3.0.3",
        "pylpsd>=0.1.4",
        "pyrp3>=1.1.0,<2.0;platform_machine=='armv7l'",  # only install on RedPitaya
        "requests==2.25.1;python_version<'3.10'",  # pinned because of bug in pip 9.0.1, see #339 # noqa: E501
        "requests>=2.25.1;python_version>='3.10'",
        "linien-common==1.0.2",
    ],
    scripts=[
        "linien_server/linien_start_server.sh",
        "linien_server/linien_stop_server.sh",
        "linien_server/linien_install_requirements.sh",
    ],
    package_data={
        "": [
            "gateware.bin",
            "linien_start_server.sh",
            "linien_stop_server.sh",
            "linien_install_requirements.sh",
        ]
    },
)
