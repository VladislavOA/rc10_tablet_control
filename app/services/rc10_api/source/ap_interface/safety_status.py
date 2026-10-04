from __future__ import annotations
from typing import TYPE_CHECKING

from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.tools import sleep
from rc10_api.source.models.classes.enum_classes.state_classes import (
    InComingSafetyStatus as Iss
)
from rc10_api.source.models.constants import CHECK_FREQUENCY_SEC
from rc10_api.source.models.type_aliases import SafetyStatus_

if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver


validate_literal = validation.validate_literal


class SafetyStatus:
    """
    Класс для работы с текущими статусами безопасности.
    Доступные статусы безопасности:
        'deinit' — Робот не инициализирован. Доступных операций нет.
        'recovery' — Нарушение ограничений в момент старта.
            Доступные методы перемещения: 'FreeDrive', 'Jogging'.
        'normal' — Рабочее состояние. Применены стандартные ограничения
            безопасности.
        'reduced' — Рабочее состояние. Применены повышенные ограничения
            безопасности.
            Снижена скорость.
        'safeguard_stop' — Экстренная останова 2-й категории, по нажатию кнопки
            безопасности.
            Без использования тормозов, с сохранением траектории.
        'emergency_stop' — Экстренная останова 1-й категории, по нажатию кнопки
            экстренного останова. С использованием тормозов, без сохранения
            траектории.
        'fault' — Экстренная останова 0-й категории, по причине внутренней
            ошибки робота. Отключение питания.
        'violation' — Экстренная останова 0-й категории, по причине нарушения
            ограничений безопасности. Отключение питания.
    """

    def __init__(self, rtd_receiver: RTDReceiver, logger: Logger) -> None:
        self._rtd_receiver = rtd_receiver
        self._logger = logger

    def get(self) -> str:
        """
        Получить текущий статус безопасности.

        Returns:
            str: Статус безопасности — ('deinit', 'recovery', 'normal',
                'reduced', 'safeguard_stop', 'emergency_stop', 'fault',
                'violation').
        """

        return Iss(self._rtd_receiver.rt_data.safety).name

    def wait(self, status: SafetyStatus_, await_sec: int = -1) -> bool:
        """
        Ожидать смену статуса безопасности.

        Args:
            status: Ожидаемый статус безопасности —
                ('recovery', 'normal', 'reduced', 'safeguard_stop').
            await_sec: Лимит времени ожидания (c).
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                условию).

        Returns:
            True: В случае успешной смены режима движения.
            False: В случае таймаута (если await_sec >= 0).
        """

        validate_literal('ss', status)
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            if self.get() == status:
                return True
        return False
