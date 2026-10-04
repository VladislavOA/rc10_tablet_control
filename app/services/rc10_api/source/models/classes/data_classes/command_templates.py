from dataclasses import dataclass, field

from rc10_api.source.models.constants import (
    CTRLR_MAX_DIG_OUT_BYTES, CTRLR_MAX_AN_OUT, WRIST_MAX_AN_IN
)
from rc10_api.source.models.type_aliases import AngleUnits, PositionOrientation


@dataclass
class MoveCommandTemplate:
    t: int = 0
    des_q: PositionOrientation = (0, ) * 6
    des_x: PositionOrientation = (0, ) * 6
    force: tuple[float, ...] = (0, ) * 6
    force_en: tuple[float, ...] = (0, ) * 6
    in_tcp: float = 0
    v_max_t: float = 0
    v_max_r: float = 0
    a_max_t: float = 0
    a_max_r: float = 0
    v_max_j: float = 0
    a_max_j: float = 0
    r_blend: float = 0
    pseg: int = -1


@dataclass
class JogCommandParametersTemplate:
    in_tcp: int = 0
    force_en: list[float] = field(default_factory=lambda: [0] * 6)
    force: list[float] = field(default_factory=lambda: [0] * 6)
    speed_max: list[float] = field(
        default_factory=lambda: [0.2] * 3 + [0.5] * 3
    )
    accel: list[float] = field(default_factory=lambda: [0.1] * 3 + [0.25] * 3)
    decel: list[float] = field(default_factory=lambda: [2.0] * 3 + [2.5] * 3)


@dataclass
class JogCommandTemplate:
    mode: int = 0
    force_en: list[float] = field(default_factory=lambda: [0] * 6)
    force_max: list[float] = field(default_factory=lambda: [0] * 6)
    force_const: list[float] = field(default_factory=lambda: [0] * 6)
    stiff: list[float] = field(default_factory=lambda: [0] * 6)
    var: list[float] = field(default_factory=lambda: [0] * 6)


@dataclass
class JointJogCommandTemplate:
    mode: int = 0
    joints_rotation_directions: list[float] = field(
        default_factory=lambda: [0] * 6
    )


@dataclass
class SetOutputTemplate:
    dig_out_mask: list[int] = field(
        default_factory=lambda: [0] * CTRLR_MAX_DIG_OUT_BYTES
    )
    dig_out: list[int] = field(
        default_factory=lambda: [0] * CTRLR_MAX_DIG_OUT_BYTES
    )
    an_out_mask: list[int] = field(
        default_factory=lambda: [0] * CTRLR_MAX_AN_OUT
    )
    an_out_curr_mode: list[int] = field(
        default_factory=lambda: [0] * CTRLR_MAX_AN_OUT
    )
    an_out_value: list[float] = field(
        default_factory=lambda: [0] * CTRLR_MAX_AN_OUT
    )


@dataclass
class InverseKinematicOptimalTemplate:
    target: list[float] = field(default_factory=lambda: [0] * 6)
    base_q: list[float] = field(default_factory=lambda: [0] * 6)


@dataclass
class MotionSetup:
    units: AngleUnits = 'deg'

    joint_speed: float = 60
    joint_acceleration: float = 80

    linear_speed: float = 0.25
    linear_acceleration: float = 0.25

    blend: float = 0


MOTION_SETUP: MotionSetup = MotionSetup()


@dataclass
class SetWristInputOutputTemplate:
    dig_out_mask: int = 0
    dig_out: int = 0
    an_in_mask: list[int] = field(
        default_factory=lambda: [0] * WRIST_MAX_AN_IN
    )
    an_in_mode: list[int] = field(
        default_factory=lambda: [0] * WRIST_MAX_AN_IN
    )
    mux_mode: int = 0
