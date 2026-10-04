from __future__ import annotations
from struct import pack
from typing import TYPE_CHECKING, Callable, cast

import rc10_api.source.features.mathematics.unit_convert as unit_c
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.tools import dataclass_to_tuple, literal_to_int
from rc10_api.source.models.classes.data_classes.command_templates import (
    MOTION_SETUP, JogCommandParametersTemplate, JointJogCommandTemplate,
    MoveCommandTemplate
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    AddWayPointCommand as Awp, Getters as Get, JointJogModes as Jm,
    Setters as Set
)
from rc10_api.source.features.tools import set_position_orientation_units
from rc10_api.source.models.classes.enum_classes.various_types import JogParamInTCP
from rc10_api.source.models.classes.enum_classes.state_classes import (
    OutComingMotionMode as Omm
)
from rc10_api.source.models.constants import (
    BLEND_LIMITS, CTRLR_GET_LAST_POSITION_UNPACK_FORMAT,
    CTRLR_JOINT_JOG_CMD_PACK_FORMAT, JOINT_ACCEL_LIMITS_DEG_SEC,
    JOINT_ACCEL_LIMITS_RAD_SEC, JOG_CMD_SET_GET_PARAMS_PACK_UNPACK_FORMAT,
    JOINT_COUNT, JOINT_SPEED_LIMITS_DEG_SEC, JOINT_SPEED_LIMITS_RAD_SEC,
    POSITION_ORIENTATION_LENGTH
)
from rc10_api.source.models.type_aliases import (
    AngleUnits, JogDirection, JointIndex, PositionOrientation,
)

if TYPE_CHECKING:
    from rc10_api.source.core.network.controller_socket import Controller
    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver


validate_index = validation.validate_index
validate_length = validation.validate_length
validate_literal = validation.validate_literal
validate_value = validation.validate_value


class JointMotion:
    """
    Класс для работы с моторным типом движения.
    """

    _controller: Controller
    _rtd_receiver: RTDReceiver

    def __init__(
        self,
        controller: Controller,
        rtd_receiver: RTDReceiver,
        add_wp: Callable
    ) -> None:
        self._controller = controller
        self._rtd_receiver = rtd_receiver
        self._add_waypoint: Callable = add_wp

    def add_new_waypoint(
        self,
        angle_pose: PositionOrientation = None,
        tcp_pose: PositionOrientation = None,
        speed: float = None,
        accel: float = None,
        blend: float = None,
        units: AngleUnits = None
    ) -> bool:
        """
        Добавить целевую точку типа движения 'Joint'. Принимает либо углы
        поворота моторов, либо координаты ЦТИ в декартовой системе координат.
        Установит робота в определенное положение, заданное углом поворота для
        каждого мотора.

        Args:
            angle_pose: 6 углов поворота моторов, от основания до фланца робота
                ('units').
            tcp_pose: Позиция ЦТИ в формате (X, Y, Z, Rx, Ry, Rz),
                где (X, Y, Z) — м, (Rx, Ry,Rz) — 'units'
            speed: Скорость моторов ('units'/c) (0-180 deg / 0-3.14 rad).
            accel: Ускорение моторов ('units'/c) (0-1500 deg / 0-26.18 rad).
            blend: Радиус сглаживания движения (м). (Радиус вокруг точки, при
                пересечении которого траекторией движения робота
                начинается/заканчивается сглаживание).
            units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
        Returns:
            True: В случае успешного добавления точки.
            False: В случае таймаута (если await_sec >= 0).
        """
        if speed is None:
            speed = MOTION_SETUP.joint_speed
        if accel is None:
            accel = MOTION_SETUP.joint_acceleration
        if blend is None:
            blend = MOTION_SETUP.blend
        if units is None:
            units = MOTION_SETUP.units
        validate_literal('angle', units)
        validate_value(blend, BLEND_LIMITS)
        validate_value(
            speed,
            (
                JOINT_SPEED_LIMITS_DEG_SEC
                if units == 'deg' else JOINT_SPEED_LIMITS_RAD_SEC
            )
        )
        validate_value(
            accel,
            (
                JOINT_ACCEL_LIMITS_DEG_SEC
                if units == 'deg' else JOINT_ACCEL_LIMITS_RAD_SEC
            )
        )
        if units == 'deg':
            speed = unit_c.degrees_to_radians(speed)
            accel = unit_c.degrees_to_radians(accel)
            if angle_pose:
                validate_length(angle_pose, POSITION_ORIENTATION_LENGTH)
                angle_pose = unit_c.degrees_to_radians(*angle_pose)
        if angle_pose:
            command = MoveCommandTemplate(
                t=Awp.move_wp_type_joint,
                des_q=angle_pose,
                v_max_j=speed,
                a_max_j=accel,
                r_blend=blend
            )
        elif tcp_pose:
            validate_length(tcp_pose, POSITION_ORIENTATION_LENGTH)
            tcp_pose = set_position_orientation_units(
                tcp_pose, units
            )
            command = MoveCommandTemplate(
                t=Awp.move_wp_type_tcp_pose,
                des_x=tcp_pose,
                des_q=self._rtd_receiver.rt_data.act_q,
                v_max_j=speed,
                a_max_j=accel,
                r_blend=blend
            )
        return self._add_waypoint(command)

    def get_actual_position(
            self, units: AngleUnits = None
    ) -> PositionOrientation:
        """
        Получить 6 углов поворотов моторов в 'Joint' формате, от основания до
        фланца робота ('units'). (Позиция определяется углом поворота для
        каждого мотора).

        Args:
            units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
        Returns:
            list: 6 углов поворотов моторов, от основания до фланца робота
                ('units').
        """

        if units is None:
            units = MOTION_SETUP.units
        validate_literal('angle', units)
        if units == 'deg':
            return cast(
                PositionOrientation,
                unit_c.radians_to_degrees(*self._rtd_receiver.rt_data.act_q)
            )
        return list(self._rtd_receiver.rt_data.act_q)

    def get_last_saved_position(
            self, units: AngleUnits = None
    ) -> PositionOrientation | None:
        """
        Получить последнюю сохраненную позицию робота.
        (6 углов поворотов моторов в 'Joint' формате, от основания до фланца
        робота ('units'). Если робот в состоянии RUN
        (когда робот снят с тормозов), функция вернет текущие углы поворотов
        моторов.

        Args:
            units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
        Returns:
            PositionOrientation: Последняя сохраненная позиция робота — 6 углов
                поворотов моторов, от основания до фланца робота ('units').
        """
        if units is None:
            units = MOTION_SETUP.units
        validate_literal('angle', units)
        self._controller.send(Get.ctrlr_coms_get_last_pos)
        response = self._controller.receive(
            Get.ctrlr_coms_get_last_pos,
            CTRLR_GET_LAST_POSITION_UNPACK_FORMAT
        )
        if units == 'deg':
            return cast(
                PositionOrientation,
                unit_c.radians_to_degrees(*response)
            )
        return cast(PositionOrientation, response)

    def jog_once(
        self, joint_index: JointIndex, jog_direction: JogDirection
    ) -> bool:
        """
        Режим 'JOINT JOGGING'. Разовая команда кратковременного движения робота
        по моторам. Команда является циклической. Для корректной работы режима
        необходимо вызывать метод в цикле, с частотой 100 Hz.

        Args:
            joint_index: Индекс мотора (0 — 5).
            jog_direction: Направление поворота мотора.
                '+' — для поворота по часовой стрелке.
                '-' — для поворота против часовой стрелки.
        Returns:
            True: В случае успешной отправки команды.
        """

        validate_index(joint_index, range(JOINT_COUNT))
        validate_literal('math', jog_direction)
        jog_template = JointJogCommandTemplate()
        jog_template.joints_rotation_directions[joint_index] = literal_to_int(
            jog_direction
        )
        jog_template.mode = Jm.ctrlr_coms_joint_jog_mode_on
        return self._controller.send(
            Omm.joint_jog,
            pack(
                CTRLR_JOINT_JOG_CMD_PACK_FORMAT,
                *dataclass_to_tuple(jog_template)
            )
        )
    
    def jog_once_all_joints(
        self, jog_directions: JogDirection
    ) -> bool:
        """
        Режим 'JOINT JOGGING'. Разовая команда кратковременного движения робота
        по моторам. Команда является циклической. Для корректной работы режима
        необходимо вызывать метод в цикле, с частотой 100 Hz.

        Args:
            jog_direction: Направление поворота мотора.
                '+' — для поворота по часовой стрелке.
                '-' — для поворота против часовой стрелки.
        Returns:
            True: В случае успешной отправки команды.
        """

        jog_template = JointJogCommandTemplate()

        for j in range(6): 
            validate_index(j, range(JOINT_COUNT))
            if jog_directions[j] != "0":
                validate_literal('math', jog_directions[j])
                jog_template.joints_rotation_directions[j] = literal_to_int(
                    jog_directions[j]
                )
        jog_template.mode = Jm.ctrlr_coms_joint_jog_mode_on
        return self._controller.send(
            Omm.joint_jog,
            pack(
                CTRLR_JOINT_JOG_CMD_PACK_FORMAT,
                *dataclass_to_tuple(jog_template)
            )
        )

    def set_jog_param_in_tcp(self, in_tcp: JogParamInTCP) -> bool:
        """
        Метод для переключения движения типа Joint между системой
        координат ЦТИ и Основания.

        Args:
            in_tcp: 1 / 0 для входа / выхода из СК ЦТИ.
        Returns:
            True: В случае успешной отправки команды.

        """
        self._controller.send(
            Set.ctrlr_coms_set_jog_param,
            pack(
                JOG_CMD_SET_GET_PARAMS_PACK_UNPACK_FORMAT,
                *dataclass_to_tuple(
                    JogCommandParametersTemplate(
                        in_tcp=in_tcp
                    )
                )
            )
        )
