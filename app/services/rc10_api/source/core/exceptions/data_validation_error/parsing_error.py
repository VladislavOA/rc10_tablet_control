class CorruptedPackageError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Received corrupted package from server'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class CommandTypeError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Server command type validation failed'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class RTDParsingError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Can not parse RT data package'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)
