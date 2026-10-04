class VersionError(Exception):
    def __init__(self, message: str = None):
        self.message = 'The client does not match the server version'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ControllerUnlockError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Server access denied'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)
