class EmergencyStopError(Exception):
    """Safety status: 5."""

    def __init__(self, message: str = None):
        self.message = 'Robot emergency stop (1-category stop event)'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ControllerFaultError(Exception):
    """Safety status: 6."""

    def __init__(self, message: str = None):
        self.message = (
            'Robot software fault (0-category stop event). Check core '
            'log-files'
        )
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class SafetyViolationError(Exception):
    """Safety status: 7."""

    def __init__(self, message: str = None):
        self.message = 'Robot safety violation (0-category stop event)'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)
