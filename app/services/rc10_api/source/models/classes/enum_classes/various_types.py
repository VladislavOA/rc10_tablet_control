from enum import Enum

from rc10_api.source.models.classes.enum_classes.base_int_enum import BaseIntEnum


class AngleUnitTypes(str, Enum):
    DEG: str = 'Градусы'
    RAD: str = 'Радианы'


class CoordinateSystemInfoType(str, Enum):
    POSITION_ORIENTATION: str = 'Позиция ориентация'
    ORIENTATION_UNITS: str = 'Единицы измерения углов'


class GUICoordinateSystem(str, Enum):
    CTI: str = 'ЦТИ'
    GLOBAL: str = 'Основание'
    LOCAL: str = 'Пользовательская'


class JogParamInTCP(BaseIntEnum):
    TRUE: int = 1
    FALSE: int = 0


class MotionTypes(str, Enum):
    JOINT: str = 'Joint'
    LINEAR: str = 'Linear'


class AddWayPointErrorCode(BaseIntEnum):
    """
    Класс ошибок добавления точки.
    Значения класса используются для определения успешности добавления
    точки и причины ошибки, если точку добавить не удалось.
    """
    success: int = 0
    buffer_full: int = 1
    out_of_limits: int = 2
    out_of_reach: int = 3
    non_finite: int = 4
    singularity: int = 5


class PowerUnitsCode(BaseIntEnum):
    V: int = 0
    mA: int = 1
