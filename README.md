LINIEN
======

<img align="right" src="https://raw.githubusercontent.com/hermitdemschoenenleben/linien/master/docs/icon.png" width="20%">

Spectroscopy locking of lasers using RedPitaya (STEMlab 125-14) that
just works. Linien aims to follow the UNIX philosophy of doing one thing
very well. It is built with Python and
[Migen](https://github.com/m-labs/migen) and is based on [RED
PID](https://github.com/quartiq/redpid).

Features
--------

-   **All included**: Modulation (up to 50 MHz), demodulation, filtering
    and servo implemented on the FPGA.
-   **Client-server architecture**: Autonomous operation on RedPitaya.
    One or multiple GUI clients can connect to the server.
-   **Autolock**: Click and drag over a line, and linien will
    automatically approach it and lock to it.
-   **Lock detection**: linien is capable of detecting loss of lock.
-   **Automatic relocking**: in that case, it can relock automatically
    using the autolock.
-   **Automatic Optimization**: linien uses machine learning to optimize
    spectroscopy parameters
-   **Remote-controllable**: The client libraries can be used to control
    or monitor the spectroscopy lock with python.
-   **Combined FMS+MTS**: Supports dual-channel spectroscopy that can be
    used to implement [combined
    FMS+MTS](https://arxiv.org/pdf/1701.01918.pdf)
-   **Logging**: Use
    [linien-influxdb](https://github.com/hermitdemschoenenleben/linien-influxdb)
    to log the lock status to influxdb.
-   **TTL status**: Outputs the lock status via TTL

![image](https://raw.githubusercontent.com/hermitdemschoenenleben/linien/master/docs/screencast.gif)

Getting started
---------------

Linien runs on Windows and Linux. For most users the [standalone
binaries](#standalone-binary) containing the graphical user interface
are recommended. If you want to use the python interface you should [install it using pip](#installation-with-pip).

### Standalone binary

You can download standalone binaries for windows and linux on [the
releases
page](https://github.com/hermitdemschoenenleben/linien/releases). On
linux you have to mark it as executable before executing:

```bash
chmod +x linien-client-linux*
```

### Installation with pip

Linien is written for python 3 and can be installed using python\'s
package manager pip:

```bash
pip3 install linien
```

Run the application by calling

```bash
linien
```

If this doesn\'t work, your local bin directory (e.g. \~/.local/bin) is
probably missing in your PATH. Alternatively you can open linien using
python:

```python
from linien.client.client import run_application
run_application()
```

Then, you can enter your RedPitaya\'s credentials and connect. If you
agree, linien\'s server component is automatically installed.

Physical setup
--------------

The default setup looks like this:

![image](https://raw.githubusercontent.com/hermitdemschoenenleben/linien/master/docs/setup.png)

You can also configure linien for different setups, e.g. if you want to
have the modulation frequency and the control on the same output. Additionally, it is possible to set up a slow integrator on ANALOG OUT 0 (0 V to 1.8 V).

![image](https://raw.githubusercontent.com/hermitdemschoenenleben/linien/master/docs/explain-pins.png)

Using the application
---------------------

# FIXME: missing

Scripting interface
-------------------

In addition to the GUI, Linien can also be controlled using python
scripts. For that purpose, installation via pip is required (see above).

```python
from linien.client.connection import BaseClient, MHz, Vpp
c = BaseClient(host, 18862, False)

# read out the modulation frequency
print(c.parameters.modulation_frequency.value / MHz)

# set modulation amplitude
c.parameters.modulation_amplitude.value = 1 * Vpp
# in the line above, we set a parameter. This is not written directly to the
# FPGA, though. In order to do this, we have to call write_data():
c.connection.root.write_data()

# plot control and error signal
import pickle
from matplotlib import pyplot as plt
plot_data = pickle.loads(c.parameters.to_plot.value)

# depending on the status (locked / unlocked), different signals are available
print(plot_data.keys())

# if unlocked, signal1 and signal2 contain the error signal of channel 1 and 2
# if the laser is locked, they contain error signal and control signal.
if c.parameters.lock.value:
    plt.plot(plot_data['control_signal'], label='control')
    plt.plot(plot_data['error_signal'], label='error')
else:
    plt.plot(plot_data['error_signal_1'], label='error 1')
    plt.plot(plot_data['error_signal_2'], label='error 2')

plt.legend()
plt.show()
```

For a full list of parameters that can be controlled or accessed have a
look at
[parameters.py](https://github.com/hermitdemschoenenleben/linien/blob/master/linien/server/parameters.py).

Development
-----------

As linien uses a git submodule, you should check it out like this:

```bash
git clone https://github.com/hermitdemschoenenleben/linien.git --recursive
```

Then, create a file named `checked_out_repo/linien/VERSION` with contents

```
dev
```
(no newlines).

This ensures that changes you made to the server component are automatically uploaded to the RedPitaya when you launch the client.

### Architecture

Linien contains three components:
* The client: Connects to the server, runs the GUI, etc.
* The server: Handles connections from the client, runs long-running tasks like the autolock or the optimization algorithm. Connects to the acquisition process for communication with the FPGA.
* The acquisition process: Handles the low-level communication with the FPGA (reading / writing registers)

The communication between the components takes place using [rpyc](https://rpyc.readthedocs.io/en/latest/).

For development purposes, you can run the first two components on your local machine to simplify debugging. Only the acquisition process has to run on the RedPitaya. In a production version of linien, server and acquisition process run on RedPitaya.

### Running the code

Before running the development version check that no production version of the server is running on the RedPitaya by executing linien\_stop\_server on the RedPitaya. Now you need to have an FPGA bitstream at `linien/server/linien.bin`. You have two choices:
* [Build the gateware](#building-the-fpga-image): this makes sense if you want to change the FPGA programming.
* Use the gateware of the latest release: if you just want to work on the python client or server code without touching the FPGA gateware, this approach is right for you as it is way easier:
    * Install linien-server using pip: `pip3 install linien-server`
    * Find out where it was installed to: `python3 -c "import linien; print(linien.__path__)"`
    * In that folder go to linien/server and copy this file to your development server folder.

Now you can launch the client

```
python3 linien/client/client.py
```

and you can connect to your RedPitaya.
If you have set `checked_out_repo/linien/VERSION` to dev ([see above](#development)), this automatically uploads your local code to the RedPitaya and starts the server.
The FPGA bitstream will also be transferred to the RedPitaya and loaded on the FPGA.

### Run server locally

For debugging it may be helpful to execute the server component on
your machine (e.g. if you want to work on the autolock and want to plot the spectra). In order to make this work, you have to start `/linien/server/acquisition_process.py` on your RedPitaya using SSH. This process provides remote access to the FPGA registers. Then, you can run the server locally and connect to the FPGA registers:

```
python3 server/server.py --remote-rp=root:password@rp-f0xxxx.local
```

Now, you can start the client. **Important**: Be sure not to connect your client to the RedPitaya, but to "localhost" instead.

### Fake server

If you just want to test the GUI, there is also a fake server that you can run locally on your machine:

```bash
python3 server/server.py --fake
```

This fake server just outputs random data. Then you can connect to \"localhost\" using the client.

### Building the FPGA image

For building the FPGA image, you need to install Xilinx Vivado first. Then, call `scripts/build\_gateware.sh`. In the end, the bitstream should be located under `linien/server/linien.bin`.
# FIXME: Windows?

### Releasing a new version

# FIXME: windows?
First, update the version number in the `checked_out_repo/linien/VERSION` file. Then you can build and upload the package to pypi using scripts/upload\_pypi.sh. Finally, build the standalone client using build\_standalone\_client.sh (you have
to do this on the platform you want to build the standalone client for).
The standalone client should be uploaded to a github release.

Troubleshooting
---------------

### Connection problems

If the client fails to connect to a RedPitaya, first check whether you
can ping it by executing

```bash
ping rp-f0xxxx.local
```

in a command line. If this works, check whether you can connect via SSH.
On Windows, you have to [install a SSH client](https://www.putty.org),
on linux you can execute

```bash
ssh rp-f0xxxx.local
```

on the command line.

FAQs
----

### Can I run linien and the RedPitaya web application / scpi interface at the same time

No, this is not possible as linien relies on a customized FPGA bitstream.

### What control bandwidth is achievable with linien?

The propagation delay is roughly 300 ns, thus approximately 3 MHz bandwidth are possible.

See Also
--------

-   [RedPID](https://github.com/quartiq/redpid): the basis of linien
