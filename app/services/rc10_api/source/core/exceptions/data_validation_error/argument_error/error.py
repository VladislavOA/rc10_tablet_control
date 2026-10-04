class ArgSignError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect sign selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgUnitsError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect units of measurement selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgValueError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect value selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgControllerStateError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect controller state selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgMotionModeError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect motion mode selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgSafetyStatusError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect safety status selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArrayLengthError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect array length'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgInputFunctionError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect input function selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgOutputFunctionError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect output function selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class ArgToolModeError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect tool mode selected'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class WristOutputActivationTypeError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Incorrect wrist output activation type'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)
