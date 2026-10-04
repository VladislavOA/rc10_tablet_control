class ServerConnectionError(Exception):
    def __init__(self, socket: int = None):
        self.message = (
            f'Server connection failed. [{socket}] port is unavailable.'
        )
        super().__init__(self.message)


class ServerPingError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Server access denied'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class BrokenConnectionError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Socket connection is broken'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class EmptyPackageError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Received empty package from server'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ClientDisconnectedError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Client has been disconnected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)
