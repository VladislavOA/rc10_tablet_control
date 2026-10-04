from __future__ import annotations
import select
from struct import pack
from typing import TYPE_CHECKING

from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation)
from rc10_api.source.core.exceptions.data_validation_error.generic_error import (
    FunctionTimeOutError, RobotCalibrationPositionError
)
from rc10_api.source.features.tools import sleep
from rc10_api.source.models.classes.enum_classes.state_classes import (
    InComingControllerState as Ics, OutComingControllerState as Ocs
)
from rc10_api.source.models.constants import (
    CHECK_FREQUENCY_SEC, CTRLR_SET_GET_STATE_PACK_UNPACK_FORMAT,
    SET_CTRLR_STATE_AWAIT_SEC
)
from rc10_api.source.models.type_aliases import ControllerState_

if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.ap_interface.motion.joint_motion import JointMotion
    from rc10_api.source.core.network.controller_socket import Controller
    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver


validate_literal = validation.validate_literal


class ControllerState:
    """
    Класс для работы с текущими состояниями контроллера.
    Доступные состояния контроллера:
        'idle' — Начальное состояние контроллера.
        'off' — Контроллер выключен.
        'stby' — Промежуточное состояние.
        'on' — Контроллер включен. Тормоза активированы.
            Если робот в состоянии 'run', ставит робота на тормоза.
            Если робот в состоянии 'off', включает робота, не снимая его с
            тормозов.
        'run' — Контроллер включен. Тормоза деактивированы.
        'calibration' — Вычисление смещения (для сохранения позиции робота
            после перезагрузки).
        'failure' — Фатальная ошибка контроллера.
        'force_exit' — Принудительное завершение работы ядра.

    При использовании 'on' и 'off', все имеющиеся целевые точки в памяти робота
        удаляются.
    """

    _controller: Controller
    _rtd_receiver: RTDReceiver
    _joint_motion: JointMotion
    _logger: Logger

    def __init__(
        self,
        controller: Controller,
        rtd_receiver: RTDReceiver,
        joint_motion: JointMotion,
        logger: Logger
    ) -> None:
        self._controller = controller
        self._rtd_receiver = rtd_receiver
        self._joint_motion = joint_motion
        self._logger = logger
        self._position_confirmed = False

    def get(self) -> str:
        """
        Получить текущее состояния контроллера.

        Returns:
            str: Состояние контроллера —
                ('idle', 'off', 'stby', 'on', 'run', 'calibration', 'failure',
                'force_exit').
        """

        return Ics(self._rtd_receiver.rt_data.state).name

    def set(
        self,
        state: ControllerState_,
        await_sec: int = SET_CTRLR_STATE_AWAIT_SEC
    ) -> bool:
        """
        Установить новое состояния контроллера.

        Args:
            state: Состояние контроллера — ('on', 'off', 'run').
            await_sec: Лимит времени ожидания (c).
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                условию).

        Returns:
            True: В случае успешной отправки команды.
        """

        validate_literal('cs', state)
        if state != Ics.run.name:
            self._position_confirmed = False
        res = self._controller.send(
            Ocs.power,
            pack(CTRLR_SET_GET_STATE_PACK_UNPACK_FORMAT, Ocs[state].value)
        )
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            if (
                self.get() == Ics.calibration.name
                or (
                    self.get() == Ics.run.name == state
                    and not self._position_confirmed
                )
            ):
                if not self._confirm_position():
                    self._compare_position()
            elif self.get() == state:
                return res
        raise FunctionTimeOutError('Controller state', await_sec)

    def _confirm_position(self) -> None | bool:
        if self._controller.socket in select.select(
            [self._controller.socket], [], [], 1
        )[0]:
            confirm = self._controller.receive(
                Ocs.confirm_position,
                CTRLR_SET_GET_STATE_PACK_UNPACK_FORMAT
            )
            if type(confirm) is tuple:
                if confirm[0] == 0:
                    pass
                else:
                    return False
        self._position_confirmed = True
        return True

    def _compare_position(self) -> bool | None:
        incorrect = []
        max_discrepancy = 5
        for index, values in enumerate(
            zip(
                self._joint_motion.get_last_saved_position('deg'),
                self._joint_motion.get_actual_position('deg')
            )
        ):
            if abs(values[0] - values[1]) > max_discrepancy:
                incorrect.append((index, values))
        if len(incorrect) > 0:
            raise RobotCalibrationPositionError(
                tuple(incorrect), max_discrepancy
            )
        return True
