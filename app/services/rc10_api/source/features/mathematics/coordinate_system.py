import numpy as np
from scipy.spatial.transform import Rotation

from rc10_api.source.ap_interface.motion.coordinate_system import CoordinateSystem
from rc10_api.source.core.exceptions.data_validation_error.generic_error import (
    CalculatePlaneError
)
from rc10_api.source.models.classes.enum_classes.various_types import (
    CoordinateSystemInfoType
)
from rc10_api.source.models.classes.data_classes.command_templates import (
    MOTION_SETUP
)
from rc10_api.source.models.constants import ORIENTATION_SLICE, POSITION_SLICE
from rc10_api.source.models.type_aliases import AngleUnits, PositionOrientation


def get_transformation_parameters(
    coordinate_system: CoordinateSystem
) -> tuple[np.array, Rotation]:
    """
    Вычисление вектора трансляции и матрицы поворота.

    Args:
        coordinate_system: Выбранная система координат.
    Returns:
        tuple: Вектор трансляции и Матрица поворота.
    """

    coordinate_system_position_orientation = np.array(
        coordinate_system.get(CoordinateSystemInfoType.POSITION_ORIENTATION)
    )
    return (
        np.array(coordinate_system_position_orientation[POSITION_SLICE]),
        Rotation.from_euler(
            'xyz',
            coordinate_system_position_orientation[ORIENTATION_SLICE],
            degrees=coordinate_system.get(
                CoordinateSystemInfoType.ORIENTATION_UNITS
            ) == 'deg'
        )
    )


def calculate_plane_from_points(
    pO: list[float, float, float] | tuple[float, float, float],
    pX: list[float, float, float] | tuple[float, float, float],
    pY: list[float, float, float] | tuple[float, float, float],
    orientation_units: AngleUnits = None
) -> PositionOrientation:
    """
    Вычисление позиции и ориентации плоскости по трем точкам.

    Args:
        p0: Точка начала координат плоскости.
        pX: Точка, определяющая направление оси X.
        pY: Точка, определяющая направление оси Y.
        orientation_units: Единицы измерения углов, в которых функция вернет
            рассчитанную ориентацию. По-умолчанию градусы.
            'deg' — градусы.
            'rad' — радианы.
    Returns:
        list: Рассчитанная позиция и ориентация плоскости.
    """

    if orientation_units is None:
        orientation_units = MOTION_SETUP.units
    pO = np.array(pO)
    pX = np.array(pX)
    pY = np.array(pY)
    if (
            np.array_equal(pO, pX)
            or np.array_equal(pO, pY)
            or np.array_equal(pX, pY)
    ):
        raise CalculatePlaneError(
            'Two or more points defining the direction of the coordinate axes '
            'of the plane coincide, the coordinates of the points must '
            'be unique.'
        )
    vecX = pX - pO
    vecY = pY - pO
    vecX_norm = vecX / np.linalg.norm(vecX)
    vecY_norm = vecY / np.linalg.norm(vecY)
    vecZ = np.cross(vecX_norm, vecY_norm)
    if np.linalg.norm(vecZ) == 0:
        raise CalculatePlaneError(
            f'The vectors {vecX} and {vecY} are collinear.'
        )
    vecZ_norm = vecZ / np.linalg.norm(vecZ)
    rotation_matrix = np.array(
        [vecX_norm, np.cross(vecZ_norm, vecX_norm), vecZ_norm]
    ).T
    rotation = Rotation.from_matrix(rotation_matrix)
    rpy = rotation.as_euler('xyz', degrees=orientation_units == 'deg')
    return pO.tolist() + rpy.tolist()


def convert_position_orientation(
    coordinate_system: CoordinateSystem,
    position_orientation: PositionOrientation,
    orientation_units: AngleUnits = None,
    to_local: bool = False,
) -> PositionOrientation:
    """
    Конвертация позиции и ориентации из одной системы координат в другую.
    По умолчанию из глобальной (основание робота) в локальную
    (пользовательскую). Переданные в функцию единицы измерения должны
    совпадать с единицами измерения методов добавления новой точки.

    Args:
        coordinate_system: Выбранная система координат.
        position_orientation: Конвертируемые позиция и ориентация в единицах
            измерения выбранной системы координат.
        orientation_units: Переданные единицы измерения. По-умолчанию градусы.
            'deg' — градусы.
            'rad' — радианы.
        to_local: Флаг переключения для конвертации из глобальной системы
            координат (основание робота) в локальную (пользовательскую).

    Returns:
        list: Новые сконвертированные позиция и ориентация.
    """
    if orientation_units is None:
        orientation_units = MOTION_SETUP.units
    position_orientation = np.array(position_orientation)
    position = position_orientation[POSITION_SLICE]
    r = Rotation.from_euler(
        'xyz',
        position_orientation[ORIENTATION_SLICE],
        degrees=orientation_units == 'deg'
    )
    translation, rotation = get_transformation_parameters(coordinate_system)
    if to_local:
        position_transformed = rotation.inv().apply(position - translation)
        orientation_transformed = (rotation.inv() * r).as_euler(
            'xyz', degrees=orientation_units == 'deg'
        )
    else:
        position_transformed = rotation.apply(position) + translation
        orientation_transformed = (rotation * r).as_euler(
            'xyz', degrees=orientation_units == 'deg'
        )
    return position_transformed.tolist() + orientation_transformed.tolist()
