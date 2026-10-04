from enum import IntEnum
from typing import Tuple


class BaseIntEnum(IntEnum):
    @classmethod
    def has_field(cls, field: str) -> bool:
        return str(field) in [member.name for member in cls]

    @classmethod
    def members_names(cls) -> Tuple[str, ...]:
        return tuple(member.name for member in cls)

    @classmethod
    def pairs(cls) -> Tuple[Tuple[str, int], ...]:
        return tuple((member.name, member.value) for member in cls)
