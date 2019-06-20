LINIEN
======

Spectroscopy locking of lasers using RedPitaya that just works.
Linien aims to follow the UNIX philosophy of doing one thing very well.
It is built with Python and `Migen <https://github.com/m-labs/migen>`_ and is based on `RED PID <https://github.com/quartiq/redpid>`_.

Features
########

* **All inclusive**: Modulation, demodulation, filtering and servo implemented on the FPGA.
* **Client-server architecture**: Autonomous operation on RedPitaya. One or multiple GUI clients can connect to the server.
* **Autolock**: Click and drag over a line, and linien will automatically approach it and lock to it.
* **Lock detection**: linien is capable of detecting loss of lock.
* **Automatic relocking**: in that case, it can relock automatically using the autolock.
* **Remote-controllable**: The client libraries can be used to control or monitor the spectroscopy lock with python.
* **Logging**: Use `linien-influxdb <https://github.com/hermitdemschoenenleben/linien-influxdb>`_ to log the lock status to influxdb.
* **GPIO**:


Getting started
###############

Linien is written in python 3 and can be installed using python's package manager pip:

..  code-block:: bash

    pip3 install linien

Run the application by calling

..  code-block:: bash

    linien

Then, you can enter your RedPitaya's credentials and connect.
The client automatically installs the server software.

Physical setup
##############




Development
###########

As linien uses a git submodule, you have to check it out like this:

..  code-block:: bash

    git clone https://github.com/hermitdemschoenenleben/linien.git --recursive


VERSION == dev erklären

Scriptable interface
####################

See Also
########

* `RedPID <https://github.com/quartiq/redpid>`_: the basis of linien