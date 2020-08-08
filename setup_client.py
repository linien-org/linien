import setuptools

import linien
assert linien.__version__ != 'dev'

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('client_requirements', 'r') as fh:
    requirements = fh.read().split(' ')

setuptools.setup(
    name="linien",
    version=linien.__version__,
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    description="Spectroscopy lock application using RedPitaya",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hermitdemschoenenleben/linien",
    packages=['linien', 'linien.communication', 'linien.client', 'linien.client.ui'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'linien=linien.client.client:run_application'
        ]
    },
    install_requires=[
        requirements
    ],
    package_data={
        # IMPORTANT: any changes have to be made in client.spec, too
        # (for the standalone installer)
        '': ['*.ui', 'VERSION', '*.ico']
    }
)