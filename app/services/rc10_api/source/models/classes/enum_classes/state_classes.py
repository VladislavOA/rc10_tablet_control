from rc10_api.source.models.classes.enum_classes.base_int_enum import BaseIntEnum


class InComingSafetyStatus(BaseIntEnum):
    """
    Класс входящих состояний безопасности.
    Значения класса используются только для сравнения значений с rt_data.
    В остальной логике программы используются только имена полей.
    """

    deinit: int = 0
    recovery: int = 1
    normal: int = 2
    reduced: int = 3
    safeguard_stop: int = 4
    emergency_stop: int = 5
    fault: int = 6
    violation: int = 7


class InComingMotionMode(BaseIntEnum):
    """
    Класс входящих режимов движения.
    Значения класса используются только для сравнения значений с rt_data.
    В остальной логике программы используются только имена полей.
    """

    hold: int = 0
    pause: int = 5
    move: int = 4
    zero_gravity: int = 1
    jog: int = 2
    joint_jog: int = 3


class OutComingMotionMode(BaseIntEnum):
    """
    Класс исходящих режимов движения.
    Значения класса используются только для отправки команд.
    В остальной логике программы используются только имена полей.
    """

    hold: int = 0
    pause: int = 4
    move: int = 2
    zero_gravity: int = 15
    jog: int = 8
    joint_jog: int = 10


class InComingControllerState(BaseIntEnum):
    """
    Класс входящих состояний контроллера.
    Значения класса используются только для сравнения значений с rt_data.
    В остальной логике программы используются только имена полей.
    """

    idle: int = 0
    off: int = 1
    stby: int = 2
    on: int = 3
    run: int = 4
    calibration: int = 5
    failure: int = 6
    force_exit: int = 7


class OutComingControllerState(BaseIntEnum):
    """
    Класс исходящих состояний контроллера.
    Значения класса используются только для отправки команд.
    В остальной логике программы используются только имена полей.
    """

    # command
    power: int = 5
    # states
    off: int = 0
    stby: int = 1
    on: int = 2
    run: int = 3
    confirm_position: int = 16


class WristMode(BaseIntEnum):
    """
    Класс режимов инструмента.
    Значения класса используются только для сравнения значений с rt_data.
    В остальной логике программы используются только имена полей.
    """

    off: int = 0
    rs485: int = 1
    analog_in: int = 2
    nc: int = 3
    gnd: int = 4


class MotionWarning(BaseIntEnum):
    """
    Класс статусов предупреждения о состоянии робота
    Значения класса используются только для сравнения значений с rt_data.
    В остальной логике программы используются только имена полей.
    """
    no_warning: int = 0
    protective_stop: int = 1
    self_collision: int = 2
