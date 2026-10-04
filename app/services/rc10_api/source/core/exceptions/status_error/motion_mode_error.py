class FunctionTimeOutError(Exception):

    def __init__(
        self,
        error_target: str = None,
        timeout_sec: float = None,
        message: str = None
    ):
        self.message = f'{error_target} did not change in {timeout_sec} sec. '
        if message:
            self.message += message
        super().__init__(self.message)
