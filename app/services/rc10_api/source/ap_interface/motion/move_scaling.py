from __future__ import annotations
from struct import pack
from typing import TYPE_CHECKING, cast

from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Getters as Get
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Setters as Set
)
from rc10_api.source.models.constants import CTRLR_SET_MOVE_SCALE_PACK_UNPACK_FORMAT

if TYPE_CHECKING:
    from rc10_api.source.core.network.controller_socket import Controller


class MoveScaling:
    """
    Класс для работы со скоростью и ускорением робота.
    """

    _controller: Controller

    def __init__(self, controller: Controller) -> None:
        self._controller = controller

    def set(self, velocity: float = 1, acceleration: float = 1) -> bool:
        """
        Установить множитель скорости и ускорения, в диапазоне (0.0 — 1.0) у.е.
        Множители применяются для типов движения 'TCP JOGGING', 'JOINT JOGGING'
        и 'RUN WAYPOINTS'.

        Args:
            velocity: Множитель скорости (0.0 — 1.0).
            acceleration: Множитель ускорения (0.0 — 1.0).

        Returns:
            True: В случае успешной отправки команды.
        """

        return self._controller.send(
            Set.ctrlr_coms_set_move_scale,
            pack(
                CTRLR_SET_MOVE_SCALE_PACK_UNPACK_FORMAT,
                velocity,
                acceleration
            )
        )

    def get(self) -> tuple[float, float] | None:
        """
        Получить текущие настройки скорости и ускорения робота.

        Returns:
            tuple: Скорость и ускорение робота.
        """

        self._controller.send(Get.ctrlr_coms_get_move_scale)
        response = self._controller.receive(
            Get.ctrlr_coms_get_move_scale,
            CTRLR_SET_MOVE_SCALE_PACK_UNPACK_FORMAT
        )
        return cast(tuple[float, float], response)
