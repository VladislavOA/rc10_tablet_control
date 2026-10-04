from __future__ import annotations
from typing import TYPE_CHECKING
from struct import pack

from rc10_api.source.ap_interface.wrist.analog_io import WristAnalogIO
from rc10_api.source.ap_interface.wrist.digital_io import WristDigitalIO
from rc10_api.source.core.exceptions.data_validation_error.generic_error import (
    FunctionTimeOutError
)
from rc10_api.source.features.tools import dataclass_to_tuple, sleep
from rc10_api.source.models.type_aliases import WristMode_
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Setters as Set,
)
from rc10_api.source.models.classes.enum_classes.state_classes import (
    WristMode as Wm
)
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.models.constants import (
    CHECK_FREQUENCY_SEC,
    CTRLR_WRIST_IO_SET_VALUE_PACK_FORMAT,
    SET_WRIST_MODE_AWAIT_SEC,
)
from rc10_api.source.models.classes.data_classes.command_templates import (
    SetWristInputOutputTemplate
)


if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver
    from rc10_api.source.core.network.controller_socket import Controller


validate_literal = validation.validate_literal
validate_length = validation.validate_length


class Wrist:
    """
    Класс для работы с платой запястья робота.
    Доступные состояния платы запястья:
        'off' — Плата запястья отсутствует.
        'rs485' — Плата запястья найдена и работает в режиме rs485 (обмен
            данными по протоколу modbus).
        'analog_in' — Плата запястья найдена и находится в режиме работы
            с аналоговыми входами.
        'nc' — Плата запястья найдена но не сконфигурирована для работы с
            внешними устройствами.
        'gnd' — Плата запястья найдена и находится в режиме общей 'земли'
            (ПРЕДУПРЕЖДЕНИЕ: не устанавливайте этот режим вручную, это может
            привести к поломке робота)
    """

    digital: WristDigitalIO
    analog: WristAnalogIO
    _rtd_receiver: RTDReceiver
    _controller: Controller

    def __init__(
        self, controller: Controller, rtd_receiver: RTDReceiver, logger: Logger
    ) -> None:
        self._rtd_receiver = rtd_receiver
        self._controller = controller
        self.digital = WristDigitalIO(controller, rtd_receiver, logger)
        self.analog = WristAnalogIO(controller, rtd_receiver, logger)
        self._position_confirmed = False

    def get(self) -> Wm:
        """
        Получить текущее состояния платы запястья.

        Returns:
            str: Состояние платы запястья. —
                ('off', 'rs485', 'analog_in', 'nc', 'gnd').
        """
        return Wm(int(self._rtd_receiver.rt_data.wrist_mode)).name

    def set(
        self, mode: WristMode_, await_sec: int = SET_WRIST_MODE_AWAIT_SEC
    ) -> bool:
        """
        Установить режим платы запястья.
        Args:
            mode: режим платы запястья. —
                ('off', 'rs485', 'analog_in', 'nc', 'gnd')
            await_sec: Лимит времени ожидания (c).
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                условию).
        Returns:
            bool: True — режим установлен, False — режим не установлен.
        """
        validate_literal('Wm', mode)
        set_input_output_template = SetWristInputOutputTemplate()
        set_input_output_template.mux_mode = Wm[mode].value
        res = self._controller.send(
            Set.ctrlr_coms_set_wrist_io,
            pack(
                CTRLR_WRIST_IO_SET_VALUE_PACK_FORMAT,
                *dataclass_to_tuple(set_input_output_template),
            ),
        )
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            if self.get() == mode:
                return res
        raise FunctionTimeOutError('Wrist mode', await_sec)
