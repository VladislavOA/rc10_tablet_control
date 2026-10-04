import math


def radians_to_degrees(*args: int | float) -> float | list[int | float]:
    """
    Перевод радианов в градусы.
    Args:
        *args: Распакованная последовательность чисел для конвертации.

    Returns:
        Кортеж конвертированных чисел.
    """

    if len(args) == 1:
        return math.degrees(float(*args))
    return [math.degrees(float(value)) for value in args]


def degrees_to_radians(*args: int | float) -> list[int | float] | float:
    """
    Перевод градусов в радианы.
    Args:
        *args: Распакованная последовательность чисел для конвертации.

    Returns:
        Кортеж конвертированных чисел.
    """
    if len(args) == 1:
        return math.radians(float(*args))
    return [math.radians(float(value)) for value in args]
