from setuptools import find_packages, setup

setup(
    name="linien-common",
    version="0.6.0.rc1",
    author="Benjamin Wiegand",
    author_email="highwaychile@posteo.de",
    maintainer="Bastian Leykauf",
    maintainer_email="leykauf@physik.hu-berlin.de",
    description="Part of linien that is used by all components.",
    long_description="Have a look at the 'linien' package for installation instructions.",  # noqa: E501
    long_description_content_type="text/x-rst",
    url="https://github.com/linien-org/linien",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.5",
    install_requires=[
        "numpy>=1.11.0",
        "scipy>=0.17.0",
        "importlib_metadata>=2.1.3",
    ],
)
