from linien_client.device import Device
from linien_client.deploy import install_remote_server

device = Device(host="rp-f0edf0.local", username="root", password="root")
install_remote_server(device)
