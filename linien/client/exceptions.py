class InvalidServerVersionException(Exception):
    def __init__(self, client_version, remote_version):
        self.client_version = client_version
        self.remote_version = remote_version

        super().__init__()


class ServerNotInstalledException(Exception):
    pass


class GeneralConnectionErrorException(Exception):
    pass