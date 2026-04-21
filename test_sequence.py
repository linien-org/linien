from linien_client.device import Device
from linien_client.connection import LinienClient

device = Device(host="rp-f0edf0.local", username="root", password="root")
client = LinienClient(device)
client.connect(autostart_server=False, use_parameter_cache=False)

client.parameters.sequence_blocks.value = [{"type": 1, "params": [0, 1, 10000000]}]
client.parameters.sequence_init_v.value = 0
client.control.write_sequence_config()
print("sequence programmed")
