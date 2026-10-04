from rc10_api.source.models.constants import TAB, TNL


class RobotCalibrationPositionError(Exception):

    def __init__(
        self,
        pos_info: tuple[tuple[int, tuple[float, float]], ...],
        max_d: int
    ):
        """
        Ошибка рассогласования углов поворотов моторов.

        Args:
            pos_info(tuple[tuple[int, tuple[float, float], float], ...]):
            Информация о позициях моторов.
                tuple[int, tuple[float, float], float]: Информация о моторе.
                    int: Индекс мотора.
                    tuple[float, float]: Сохраненная и текущая позиции.
                    float: Разница углов.
            max_d: Максимально допустимая разница в градусах между последней
                сохраненной и текущей позицией.
        """

        self.message = 'Robot position discrepancy. Manual calibration needed'
        rows = []
        for tuple_ in pos_info:
            rows.append(
                f'{TNL}    Joint {tuple_[0]}: [Saved: {tuple_[1][0]},'
                f'{TAB}Actual:{tuple_[1][1]}]'
            )
        self.message += (
            f'{TNL}Discrepancy between the current and last saved positions '
            f'is more than {max_d} degrees:\n'
            f'{"".join(rows)}'
        )

        super().__init__(self.message)


class CalculatePlaneError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Failed to calculate plane using three points'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class FunctionTimeOutError(Exception):

    def __init__(
        self,
        error_target: str = None,
        timeout_sec: float = None,
        message: str = None
    ):
        self.message = f'{error_target} did not change in {timeout_sec} sec'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class AddWaypointError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Failed to add the waypoint'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class WristStateError(Exception):
    def __init__(self, message: str = None):
        self.message = 'Wrist in off state. Check connection'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)


class WristAIOUnitsNotSet(Exception):
    def __init__(self, message: str = None):
        self.message = 'Failed to set analog inputs units'
        if message:
            self.message = self.message + f' ({message})'
        super().__init__(self.message)
