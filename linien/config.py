ACQUISITION_PORT = 19321
DEFAULT_SERVER_PORT = 18862
REMOTE_BASE_PATH = "/linien"
DEFAULT_RAMP_SPEED = (125 * 2048) << 6
# IMPORTANT: DEFAULT_COLORS and N_COLORS have to be here, not in client.config
# because the server needs them and shouldn't import client config as it requires
# additional packages
DEFAULT_COLORS = [
    (200, 0, 0, 200),
    (0, 200, 0, 200),
    (0, 0, 200, 200),
    (200, 200, 0, 200),
]
N_COLORS = len(DEFAULT_COLORS)
