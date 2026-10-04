from __future__ import annotations
from struct import pack
from typing import TYPE_CHECKING, cast

from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Getters as Get, Setters as Set
)
from rc10_api.source.models.constants import (
    CTRLR_SET_GET_PAYLOAD_PACK_UNPACK_FORMAT, TCP_POSITION_COUNT
)

if TYPE_CHECKING:
    from rc10_api.source.core.network.controller_socket import Controller


validate_length = validation.validate_length


class PayLoad:
    """
    Класс для работы с полезной нагрузкой робота.
    """
    _controller: Controller

    def __init__(self, controller: Controller) -> None:
        self._controller = controller

    def set(
        self, mass: float, tcp_mass_center: tuple[float, float, float]
    ) -> bool:
        """
        Установить массу и центр массы полезной нагрузки.
        Максимальная допустимая грузоподъемность составляет 10 кг,
        при центре масс, расположенном в нулевых координатах фланца.

        Args:
            mass: Масса полезной нагрузки.
            tcp_mass_center: Центр массы в системе координат фланца,
                в формате (X, Y, Z), где (X, Y, Z) — м.
        Returns:
            True: В случае успешной отправки команды.
        """

        validate_length(tcp_mass_center, TCP_POSITION_COUNT)
        return self._controller.send(
            Set.ctrlr_coms_set_payload,
            pack(
                CTRLR_SET_GET_PAYLOAD_PACK_UNPACK_FORMAT,
                mass,
                *tcp_mass_center
            )
        )

    def get(self) -> tuple[float, tuple[float, float, float]] | None:
        """
        Получить текущие настройки массы и центра массы полезной нагрузки.

        Returns:
            tuple: Масса полезной нагрузки и центр массы в системе координат
                фланца, в формате (X, Y, Z), где (X, Y, Z) — м.
        """

        self._controller.send(Get.ctrlr_coms_get_payload)
        response = self._controller.receive(
            Get.ctrlr_coms_get_payload,
            CTRLR_SET_GET_PAYLOAD_PACK_UNPACK_FORMAT
        )
        return cast(
            tuple[float, tuple[float, float, float]],
            (response[0], response[1:])
        )
