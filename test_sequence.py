from linien_client.device import Device
from linien_client.connection import LinienClient
import random

device = Device(host="rp-f0edf0.local", username="root", password="root")
client = LinienClient(device)
client.connect(autostart_server=False, use_parameter_cache=False)

vals = []
for i in range(1024):
    if i < 160:
        vals.append(8000 - i * 50)
    elif i < 320:
        vals.append(i * 50)
    elif i < 640:
        vals.append(0)
    elif i < 1024:
        vals.append(8000)

client.control.write_awg(vals)

client.parameters.sequence_blocks.value = [
    {"type": 5, "params": [10, 100000000]},
    {"type": 1, "params": [0, 80, 400000000]},
    {"type": 0, "params": [1000, 400000000]},
    {"type": 4, "params": [0, 8000, -8000, 800, 8000, 400000000]},
    {"type": 0, "params": [4000, 400000000]},
    {"type": 4, "params": [0, 2000, -1000, 800, 1000, 400000000]},
    {"type": 4, "params": [0, 8000, -1000, 3000, 1000, 400000000]},
    {"type": 0, "params": [8000, 400000000]},
    {"type": 4, "params": [2000, 8000, -1000, 3000, 1000, 400000000]},
    {"type": 1, "params": [0, 5000, 400000000]},
    {"type": 4, "params": [6000, 1000, -1000, 8000, 1000, 400000000]},
    # {"type": 4, "params": [0000, 1000, -8000, 8000, 1000, 400000000]},
    # {"type": 4, "params": [1000, 1000, -8000, 8000, 2000, 400000000]},
    # {"type": 4, "params": [4000, 1000, -8000, 8000, 4000, 400000000]},
    # {"type": 4, "params": [6000, 1000, -8000, 8000, 8000, 400000000]},
    # {"type": 4, "params": [8000, 1000, -8000, 8000, 10000, 400000000]},
]
client.control.write_sequence_config()
print("sequence programmed")
