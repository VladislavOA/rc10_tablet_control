class ControllerFailureError(Exception):
    """Controller state: 6."""

    def __init__(self, message: str = None):
        self.message = (
            'Controller inner error happened. Controller reboot needed'
        )
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)
