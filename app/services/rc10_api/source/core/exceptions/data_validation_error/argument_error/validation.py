
import re
from typing import Iterable, Sized

from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    error as err
)
from rc10_api.source.models.classes.enum_classes.io_functions import (
    InputFunction, OutputFunction
)
from rc10_api.source.models.classes.enum_classes.state_classes import (
    InComingSafetyStatus as Iss, OutComingControllerState as Ocs,
    OutComingMotionMode as Omm, WristMode as Wm
)
from rc10_api.source.models.constants import ALLOWED_GUI_ENTRY_SYMBOLS
from rc10_api.source.models.type_aliases import (
    AngleUnits, CompareSigns, ControllerState_, JogAxis, JogDirection,
    LiteralType, MotionMode_, PowerUnits, SafetyStatus_
)


def validate_literal(
    type_: LiteralType,
    value: (
        CompareSigns | JogDirection | AngleUnits | PowerUnits | JogAxis
        | ControllerState_ | MotionMode_ | SafetyStatus_
    )
):
    if type_ == 'compare':
        if value not in ('>', '<'):
            raise err.ArgSignError(value)
    elif type_ == 'math':
        if value not in ('+', '-'):
            raise err.ArgSignError(value)
    elif type_ == 'angle':
        if value not in ('deg', 'rad'):
            raise err.ArgUnitsError(value)
    elif type_ == 'power':
        if value not in ('mA', 'V'):
            raise err.ArgUnitsError(value)
    elif type_ == 'axis':
        if value not in ('X', 'Y', 'Z', 'Rx', 'Ry', 'Rz'):
            raise err.ArgValueError(value)
    elif type_ == 'activation_type':
        if value not in ('hold', 'trigger'):
            raise err.WristOutputActivationTypeError(value)
    elif type_ == 'cs':
        if not Ocs.has_field(value):
            raise err.ArgControllerStateError(value)
    elif type_ == 'mm':
        if not Omm.has_field(value):
            raise err.ArgMotionModeError(value)
    elif type_ == 'ss':
        if not Iss.has_field(value):
            raise err.ArgSafetyStatusError(value)
    elif type_ == 'in_f':
        if not InputFunction.has_field(value):
            raise err.ArgInputFunctionError(value)
    elif type_ == 'out_f':
        if not OutputFunction.has_field(value):
            raise err.ArgOutputFunctionError(value)
    elif type_ == 'Wm':
        if not Wm.has_field(value):
            raise err.ArgToolModeError(value)


def validate_index(index: int, range_: Iterable):
    if index not in range_:
        raise err.ArgValueError(str(index))


def validate_value(value: float, gap: tuple[float | None, float | None]):
    """
    Проверка числа на вхождение в промежуток.

    Args:
        value: Число для проверки.
        gap(tuple): Ограничения промежутка (промежуток включает границы).
            (None, int) — промежуток с ограничением по верхнему значению.
            (int, None) — промежуток с ограничением по нижнему значению.
            (int, int) — промежуток с ограничениями по верхнему и нижнему
                значениям.

    Returns:
        None: В случае прохождения проверки.
    Raises:
        ArgValueError: В случае неуспешного прохождения проверки.
    """

    if gap[0] is None:
        if value <= gap[1]:
            return
    elif gap[1] is None:
        if gap[0] <= value:
            return
    elif gap[0] <= value <= gap[1]:
        return
    raise err.ArgValueError(str(value))


def validate_length(obj: Sized, length: int):
    if len(obj) < length:
        raise err.ArrayLengthError


def validate_gui_entry(entry_text):
    return True if re.match(ALLOWED_GUI_ENTRY_SYMBOLS, entry_text) else False
