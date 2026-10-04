import time
from dataclasses import fields
from datetime import datetime
from signal import SIGINT, SIGTERM, signal
from typing import Any, Callable, Generator, Tuple

import rc10_api.source.features.mathematics.unit_convert as unit_c
from rc10_api.source.models.constants import ORIENTATION_SLICE, POSITION_SLICE
from rc10_api.source.models.type_aliases import AngleUnits, PositionOrientation


def dataclass_to_tuple(class_object: Any) -> Tuple[Any, ...]:
    """
    Конвертация всех полей дата-класса в один общий кортеж.
    В процессе конвертации происходит распаковка всех списков и кортежей из
    полей класса.

    Args:
        class_object: Объект дата-класса для распаковки.

    Returns:
        tuple: Значения полей дата-класса (списки и кортежи распакованы).
    """

    unpacked_values = ()
    for field in fields(class_object):
        value = getattr(class_object, field.name)
        if isinstance(value, (list, tuple)):
            unpacked_values += tuple(value)
        else:
            unpacked_values += (value,)
    return unpacked_values


def register_execute_func_before_terminate(func: Callable):
    signal(SIGINT, lambda _, __: func())
    signal(SIGTERM, lambda _, __: func())


def sleep(
    await_sec: int | float = -1, frequency: int | float = 0.005
) -> Generator[float, int | float, None]:
    start_time = datetime.now()
    while True:
        current_sec = (
            await_sec
            if await_sec < 0 else (datetime.now() - start_time).total_seconds()
        )
        if current_sec > await_sec:
            return time.sleep(frequency)
        time.sleep(frequency)
        yield round(await_sec - current_sec, 3)


def literal_to_int(value: str | int | float) -> int | float:
    signs = {'-': -1, '+': 1}
    axis = ('X', 'Y', 'Z', 'Rx', 'Ry', 'Rz')
    if value in axis:
        return axis.index(value)
    elif value in signs.keys():
        return signs.get(value)
    elif type(value) in [int, float]:
        return value
    else:
        return 0


def set_position_orientation_units(
    position_orientation: PositionOrientation,
    orientation_units: AngleUnits
):
    """
    Метод для перевода градусов в радианы в переданных позиции и ориентации.
    """

    return (
        list(position_orientation[POSITION_SLICE])
        + unit_c.degrees_to_radians(
            *position_orientation[ORIENTATION_SLICE]
        )
    ) if orientation_units == 'deg' else position_orientation
