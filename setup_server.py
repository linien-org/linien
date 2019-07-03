import setuptools
import subprocess

import linien
assert linien.__version__ != 'dev'

setuptools.setup(
    name="linien-server",
    version=linien.__version__,
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    description="Server of linien that runs on RedPitaya.",
    long_description="Have a look at the \"linien\" package for installation instructions.",
    long_description_content_type="text/x-rst",
    url="https://github.com/hermitdemschoenenleben/linien",
    packages=['linien', 'linien.communication', 'linien.server'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'rpyc>=4.1.0', 'myhdl', 'click'
    ],
    scripts=[
        'linien/server/linien_start_server',
        'linien/server/linien_stop_server',
        'linien/server/linien_install_requirements'
    ],
    package_data={
        '': ['redpid.bin', 'linien_start_server', 'linien_stop_server',
             'linien_install_requirements', 'VERSION']
    }
)