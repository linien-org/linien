apt-get install screen
pip3 install rpyc


git clone https://github.com/RedPitaya/RedPitaya.git
cd RedPitaya/Test/monitoradvanced
make
cp monitoradvanced /usr/bin

# install pyrp3
git clone https://github.com/hermitdemschoenenleben/pyrp3.git
cd pyrp3
python3 setup.py install
cd ../
pip3 install myhdl

# install pyrp2
git clone https://github.com/hermitdemschoenenleben/pyrp.git
cd pyrp
python2.7 setup.py install
apt-get install python-pip python-numpy
#wget https://bootstrap.pypa.io/ez_setup.py -O - | python
#pip2 install myhdl

# build monitor shared library
cd monitor
make
cp libmonitor.so /usr/lib/
