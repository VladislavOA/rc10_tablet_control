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
    GRAVITY_VECTOR_COUNT, CTRLR_SET_GET_GRAVITY_PACK_UNPACK_FORMAT
)

if TYPE_CHECKING:
    from rc10_api.source.core.network.controller_socket import Controller


validate_length = validation.validate_length


class ControllerGravity:
    """
    Класс для управления ориентацией контроллера через задание вектора
    гравитации. Изменяет физическое положение/ориентацию контроллера путем
    имитации заданного вектора гравитационного воздействия.
    """
    _controller: Controller

    def __init__(self, controller: Controller) -> None:
        self._controller = controller

    def set(self, gravity_vector: tuple[float, float, float]) -> bool:
        """
        Установить вектор гравитации, нормированный на g = -9.81 м/с². Вектор
        должен быть нормирован до передачи в в метод.

        Args:
            gravity_vector: Вектор гравитации,в формате (X, Y, Z),
                где (X, Y, Z) — м/с².
        Returns:
            True: В случае успешной отправки команды, иначе False
        """

        validate_length(gravity_vector, GRAVITY_VECTOR_COUNT)
        inverted_vector = (
            -gravity_vector[0],
            -gravity_vector[1],
            -gravity_vector[2]
        )
        return self._controller.send(
            Set.ctrlr_coms_set_gravity,
            pack(
                CTRLR_SET_GET_GRAVITY_PACK_UNPACK_FORMAT,
                *inverted_vector
            )
        )

    def get(self) -> tuple[float, float, float] | None:
        """
        Получить текущий активный вектор гравитации, нормированный
            на g = -9.81 м/с².

        Returns:
            tuple: Вектор гравитации, в формате (X, Y, Z),
                где (X, Y, Z) — м/с².
        """

        self._controller.send(Get.ctrlr_coms_get_gravity)
        response = self._controller.receive(
            Get.ctrlr_coms_get_gravity,
            CTRLR_SET_GET_GRAVITY_PACK_UNPACK_FORMAT
        )
        inverted_response = (-response[0], -response[1], -response[2])
        return cast(tuple[float, float, float], inverted_response)
