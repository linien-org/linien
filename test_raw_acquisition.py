from linien.client.connection import LinienClient
import pickle

l = LinienClient({"host": "192.168.123.24", "username": "root", "password": "root"})
l.parameters.acquisition_raw_enabled.value = True
l.connection.root.write_registers()

from time import sleep

sleep(1)

d = pickle.loads(l.parameters.acquisition_raw_data.value)
print(d)
