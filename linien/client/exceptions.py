class ServerNotRunningException(Exception):
    def __init__(self):
        super().__init__(
            "The host was reached but no linien server is running. Use `autostart_server` if you want to change this."
        )


class InvalidServerVersionException(Exception):
    def __init__(self, client_version, remote_version):
        self.client_version = client_version
        self.remote_version = remote_version

        super().__init__(
            "Version mismatch: Client is %s and server is %s"
            % (client_version, remote_version)
        )


class ServerNotInstalledException(Exception):
    pass


class GeneralConnectionErrorException(Exception):
    pass
