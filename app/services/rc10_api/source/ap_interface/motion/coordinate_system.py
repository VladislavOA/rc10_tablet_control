from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.models.classes.enum_classes.various_types import (
    CoordinateSystemInfoType
)
from rc10_api.source.models.classes.data_classes.command_templates import (
    MOTION_SETUP
)
from rc10_api.source.models.constants import POSITION_ORIENTATION_LENGTH
from rc10_api.source.models.type_aliases import AngleUnits, PositionOrientation

validate_length = validation.validate_length
validate_literal = validation.validate_literal


class CoordinateSystem:
    """
    Класс для работы с координатными системами робота.
    """

    def __init__(
        self,
        position_orientation: PositionOrientation,
        orientation_units: AngleUnits = None
    ) -> None:
        if orientation_units is None:
            orientation_units = MOTION_SETUP.units
        self._set_coordinate_system(position_orientation, orientation_units)

    def set(
        self,
        position_orientation: PositionOrientation,
        orientation_units: AngleUnits = None
    ) -> None:
        """
        Установка новых значений пользовательской системы координат.

        Args:
            position_orientation: Нулевая точка пользовательской системы
                координат в формате (X, Y, Z, Rx, Ry, Rz), где (X, Y, Z) — м,
                (Rx, Ry,Rz) — 'orientation_units'. Задается в координатной
                системе основания робота.
            orientation_units: Единицы измерения. По-умолчанию градусы.
        """

        if orientation_units is None:
            orientation_units = MOTION_SETUP.units
        self._set_coordinate_system(position_orientation, orientation_units)

    def get(
        self, info_type: CoordinateSystemInfoType
    ) -> PositionOrientation | AngleUnits:
        """
        Получение текущей активной системы координат или единиц измерения
        заданной СК.

        Args:
            info_type: enum класса CoordinateSystemInfoType, отвечает за
                тип возвращаемой информации.
                    POSITION_ORIENTATION: 'Позиция ориентация'.
                    ORIENTATION_UNITS: 'Единицы измерения углов'.
        Returns:
            list: Текущая нулевая точка пользовательской системы координат
                в формате (X, Y, Z, Rx, Ry, Rz), где (X, Y, Z) — м,
                (Rx, Ry,Rz) — 'orientation_units'.
            str: Единицы измерения углов.
        """

        if info_type == CoordinateSystemInfoType.POSITION_ORIENTATION:
            return self.position_orientation
        elif info_type == CoordinateSystemInfoType.ORIENTATION_UNITS:
            return self.orientation_units

    def _set_coordinate_system(
        self,
        position_orientation: PositionOrientation,
        orientation_units: AngleUnits
    ) -> None:
        """
        Метод для установки системы координат и единиц измерения с валидацией
        входных данных.

        Args:
            position_orientation: Система координат в формате
                (X, Y, Z, Rx, Ry, Rz).
            orientation_units: Единицы измерения углов.
        """

        validate_literal('angle', orientation_units)
        validate_length(position_orientation, POSITION_ORIENTATION_LENGTH)
        self.position_orientation = position_orientation
        self.orientation_units = orientation_units
