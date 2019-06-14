# the server is started in a screen session
apt-get install screen
pip3 install rpyc myhdl

# monitoradvanced is required for manipulating FPGA registers
cd /tmp
git clone https://github.com/RedPitaya/RedPitaya.git
cd RedPitaya/Test/monitoradvanced
make
cp monitoradvanced /usr/bin

# install pyrp3
cd /tmp
git clone https://github.com/hermitdemschoenenleben/pyrp3.git
cd pyrp3
python3 setup.py install
cd ../
pip3 install myhdl

# build monitor shared library
cd monitor
make
cp libmonitor.so /usr/lib/
