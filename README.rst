LINIEN
======

Spectroscopy locking of lasers using RedPitaya (STEMlab 125-14) that just works.
Linien aims to follow the UNIX philosophy of doing one thing very well.
It is built with Python and `Migen <https://github.com/m-labs/migen>`_ and is based on `RED PID <https://github.com/quartiq/redpid>`_.

Features
########

* **All inclusive**: Modulation (up to 50 MHz), demodulation, filtering and servo implemented on the FPGA.
* **Client-server architecture**: Autonomous operation on RedPitaya. One or multiple GUI clients can connect to the server.
* **Autolock**: Click and drag over a line, and linien will automatically approach it and lock to it.
* **Lock detection**: linien is capable of detecting loss of lock.
* **Automatic relocking**: in that case, it can relock automatically using the autolock.
* **Remote-controllable**: The client libraries can be used to control or monitor the spectroscopy lock with python.
* **Combined FMS+MTS**: Supports dual-channel spectroscopy that can be used to implement `combined FMS+MTS <https://arxiv.org/pdf/1701.01918.pdf>`_
* **Logging**: Use `linien-influxdb <https://github.com/hermitdemschoenenleben/linien-influxdb>`_ to log the lock status to influxdb.
* **TTL status**: Outputs the lock status via TTL


Getting started
###############

Linien runs on Windows and Linux. It is written for python 3 and can be installed using python's package manager pip:

..  code-block:: bash

    pip3 install linien

Run the application by calling

..  code-block:: bash

    linien

If this doesn't work, your local bin directory (e.g. ~/.local/bin) is probably missing in your PATH.
Alternatively you can open linien using python:

..  code-block:: python

    from linien.client.client import run_application
    run_application()

Then, you can enter your RedPitaya's credentials and connect. If you agree, linien's server component is automatically installed.

Physical setup
##############

Scriptable interface
####################

Linien running on RedPitaya can not only be controlled using the GUI but also by python scripts.

..  code-block:: python

    from linien.client.connection import BaseClient, MHz, Vpp
    c = BaseClient(host, 18862, False)

    # read out the modulation frequency
    print(c.parameters.modulation_frequency.value / MHz)

    # set modulation amplitude
    c.parameters.modulation_amplitude.value = 1 * Vpp
    c.connection.root.write_data()

    import pickle
    from matplotlib import pyplot as plt
    plot_data = pickle.loads(c.parameters.to_plot.value)
    signal1, signal2 = plot_data

    # if unlocked, signal1 and signal2 contain the error signal of channel 1 and 2
    # if the laser is locked, they contain error signal and control signal.
    plt.plot(signal1)
    plt.plot(signal2)
    plt.show()

For a full list of parameters that can be controlled have a look at `parameters.py <https://github.com/hermitdemschoenenleben/linien/blob/master/linien/server/parameters.py>`_.

Development
###########

As linien uses a git submodule, you have to check it out like this:

..  code-block:: bash

    git clone https://github.com/hermitdemschoenenleben/linien.git --recursive

To simplify development of the server component, its source code is automatically uploaded to the RedPitaya. For that, edit the `VERSION` file and replace it's content with `dev`. Check that no server is running on the RedPitaya and start the client. Your development code should be uploaded to /linien and the linien server is started from that directory.

Fake server for testing the GUI:

..  code-block:: bash

    python3 server/server.py --fake

Run server locally and control:

    python3 server/server.py --remote-rp=root:password@rp-f0xxxx.local

For this, `acquisition_process.py` has to be started on the RedPitaya.


In order to build the FPGA image, use `scripts/build_gateware.sh`.

See Also
########

* `RedPID <https://github.com/quartiq/redpid>`_: the basis of linien