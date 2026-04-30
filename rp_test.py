from linien_client.deploy import install_remote_server
from linien_client.device import Device

device = Device(host="rp-f0edf0.local", username="root", password="root")
install_remote_server(device)
