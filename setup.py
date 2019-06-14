import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="linien",
    version="0.0.2",
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    description="Spectroscopy lock application using RedPitaya",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/hermitdemschoenenleben/linien",
    packages=['linien', 'linien.communication', 'linien.client', 'linien.client.ui', 'linien.server'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'gui_scripts': [
            'linien=linien.client.client:run_application',
        ],
    },
    install_requires=[
        'numpy', 'PyQt5', 'rpyc', 'appdirs', 'pyqtgraph', 'scipy', 'paramiko'
    ],
    include_package_data=True
)