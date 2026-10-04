from __future__ import annotations
from struct import pack
from typing import cast, TYPE_CHECKING

import rc10_api.source.features.mathematics.unit_convert as unit_c
from rc10_api.source.ap_interface.motion.joint_motion import JointMotion
from rc10_api.source.ap_interface.motion.kinematics_solution import Kinematics
from rc10_api.source.ap_interface.motion.linear_motion import LinearMotion
from rc10_api.source.ap_interface.motion.motion_mode import MotionMode
from rc10_api.source.ap_interface.motion.move_scaling import MoveScaling
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.core.exceptions.data_validation_error.generic_error import (
    AddWaypointError
)
from rc10_api.source.features.gui.ui_controller import SimpleJoystickUI
from rc10_api.source.features.tools import dataclass_to_tuple, sleep
from rc10_api.source.models.classes.data_classes.command_templates import (
    MOTION_SETUP, MoveCommandTemplate
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    AddWayPointCommand as Awp, Getters as Get, Setters as Set
)
from rc10_api.source.models.classes.enum_classes.state_classes import (
    OutComingMotionMode as Omm
)
from rc10_api.source.models.classes.enum_classes.various_types import (
    AddWayPointErrorCode as AwpErr
)
from rc10_api.source.models.constants import (
    ADD_WAY_POINT_ERROR_DESCRIPTION, CTRLR_ADD_WP_CMD_PACK_FORMAT,
    CTRLR_GET_SET_HOME_POSE_PACK_UNPACK_FORMAT,
    MOVE_TO_HOME_POSE_ACCEL, MOVE_TO_HOME_POSE_SPEED,
    OMM_ENABLE_DISABLE_PACK_FORMAT, WP_ADD_TIMEOUT, CHECK_FREQUENCY_SEC,
    POSITION_ORIENTATION_LENGTH, WP_COUNT_LIMITS, WP_COUNTER_MAX_VALUE,
    CTRLR_COMS_ADD_WP_RES_FORMAT
)
from rc10_api.source.models.type_aliases import AngleUnits, PositionOrientation

if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.ap_interface.motion.coordinate_system import (
        CoordinateSystem
    )
    from rc10_api.source.core.network.controller_socket import Controller
    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver


validate_length = validation.validate_length
validate_literal = validation.validate_literal
validate_value = validation.validate_value


class Motion:

    _controller: Controller
    _rtd_receiver: RTDReceiver

    joint: JointMotion
    linear: LinearMotion
    scale_setup: MoveScaling
    mode: MotionMode
    kinematics: Kinematics

    def __init__(
        self, controller: Controller, rtd_receiver: RTDReceiver, logger: Logger
    ) -> None:

        self._logger = logger
        self._controller = controller
        self._rtd_receiver = rtd_receiver

        self.joint = JointMotion(
            self._controller, rtd_receiver, self._add_waypoint
        )
        self.linear = LinearMotion(
            self._controller, rtd_receiver, self._add_waypoint
        )
        self.scale_setup = MoveScaling(self._controller)
        self.mode = MotionMode(self._controller, rtd_receiver, self._logger)
        self.kinematics = Kinematics(self._controller, self.joint)
        self.waypoint_setup = None
        self._waypoint_counter = None

    def _add_waypoint(self, command_template: MoveCommandTemplate) -> bool:
        """
        Полный функционал добавления целевой точки (рад, м, с) в системе
        координат основания робота.

        Args:
            command_template: Предзаполненный объект дата-класса, содержащий
            все необходимые поля для команды.

        Returns:
            True: В случае успешного добавления точки.

        Raises:
            AddWaypointError: В случае таймаута ожидания добавления точки.
        """

        if self._waypoint_counter is None:
            self._waypoint_counter = self._rtd_receiver.rt_data.wp_cntr
        self._waypoint_counter = (
            (self._waypoint_counter + 1) & WP_COUNTER_MAX_VALUE
        )
        self._controller.send(
            Awp.ctrlr_coms_move_add_wp,
            pack(
                CTRLR_ADD_WP_CMD_PACK_FORMAT,
                *dataclass_to_tuple(command_template)
            )
        )
        response = self._controller.receive(
            Awp.ctrlr_coms_move_add_wp, CTRLR_COMS_ADD_WP_RES_FORMAT)
        if response[0] != AwpErr.success:
            self._waypoint_counter = None
            raise AddWaypointError(
                ADD_WAY_POINT_ERROR_DESCRIPTION[response[0]])
        for _ in sleep(
            await_sec=WP_ADD_TIMEOUT, frequency=CHECK_FREQUENCY_SEC
        ):
            if self._rtd_receiver.rt_data.wp_cntr == self._waypoint_counter:
                return True
        self._waypoint_counter = None
        raise AddWaypointError

    @staticmethod
    def set_motion_config(
        units: AngleUnits = None,
        joint_speed: float = None,
        joint_acceleration: float = None,
        linear_speed: float = None,
        linear_acceleration: float = None,
        blend: float = None
    ):
        """
        Установка глобальной настройки для линейного и моторного типов
        движения.

        Args:
            units: Единицы измерения.
                'deg' — градусы.
                'rad' — радианы.
            joint_speed: Скорость моторов ('units'/c) (0-180 deg / 0-3.14 rad).
            joint_acceleration: Ускорение моторов ('units'/c)
                (0-1500 deg / 0-26.18 rad).
            linear_speed: Скорость перемещения точки (0 - 3 м/с).
            linear_acceleration: Ускорение перемещения точки (0 - 15 м/c^2).
            blend: Радиус сглаживания движения (м).
                (Радиус вокруг точки, при пересечении которого траекторией
                движения робота начинается/заканчивается сглаживание).
        """

        if units:
            MOTION_SETUP.units = units
        if joint_speed:
            MOTION_SETUP.joint_speed = joint_speed
        if joint_acceleration:
            MOTION_SETUP.joint_acceleration = joint_acceleration
        if linear_speed:
            MOTION_SETUP.linear_speed = linear_speed
        if linear_acceleration:
            MOTION_SETUP.linear_acceleration = linear_acceleration
        if blend:
            MOTION_SETUP.blend = blend

    def check_waypoint_completion(self, waypoint_count: int = 0) -> bool:
        """
        Проверить состояние исполнения текущих заданных целевых точек
        (без ожидания).

        Args:
            waypoint_count: Целевое количество точек в очереди
        Returns:
            True: Если точки исполнены (целевых точек в буфере меньше, чем
                `waypoint_count`).
            False: Если точки не исполнены (точек в буфере больше, чем
                `waypoint_count`).
        """

        validate_value(waypoint_count, WP_COUNT_LIMITS)
        return (self._rtd_receiver.rt_data.buff_fill <= waypoint_count)

    def get_home_pose(self, units: AngleUnits = None) -> PositionOrientation:
        """
        Получить текущую домашнюю позицию робота.

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
        self._controller.send(Get.ctrlr_coms_get_home_pose)
        response = self._controller.receive(
            Get.ctrlr_coms_get_home_pose,
            CTRLR_GET_SET_HOME_POSE_PACK_UNPACK_FORMAT
        )
        if units == 'deg':
            return cast(
                PositionOrientation,
                unit_c.radians_to_degrees(*response)
            )
        return cast(PositionOrientation, response)

    def free_drive(self, enable: bool = True) -> bool:
        """
        Режим 'FREE DRIVE'. Позволяет управлять роботом вручную.
        Команда является циклической. Для корректной работы режима необходимо
        вызывать метод в цикле, с частотой 100 Hz.

        Args:
            enable: Состояние режима.
        Returns:
            True: В случае успешной отправки команды.
        """

        return self._controller.send(
            Omm.zero_gravity,
            pack(OMM_ENABLE_DISABLE_PACK_FORMAT, bool(enable))
        )

    def move_to_home_pose(self):
        """
        Передвинуть робота в домашнюю позицию. Предварительно происходит
        остановка робота и сброс точек в буфере.

        Returns:
            True: В случае начала перемещения в домашнюю позицию.
        """
        return (
            self.mode.set('hold')
            and
            self.joint.add_new_waypoint(
                angle_pose=self.get_home_pose(units='rad'),
                speed=MOVE_TO_HOME_POSE_SPEED,
                accel=MOVE_TO_HOME_POSE_ACCEL,
                units='rad'
            )
            and
            self.mode.set('move')
        )

    def set_home_pose(
        self,
        angle_pose: PositionOrientation = None,
        units: AngleUnits = None
    ) -> bool:
        """
        Установить новую домашнюю позицию робота.

        Args:
            angle_pose: 6 углов поворота моторов, от основания до фланца робота
                ('units').
            units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
        Returns:
            True: В случае успешно установленной домашней позиции.
        """
        if units is None:
            units = MOTION_SETUP.units
        validate_literal('angle', units)
        validate_length(angle_pose, POSITION_ORIENTATION_LENGTH)
        if units == 'deg':
            angle_pose = unit_c.degrees_to_radians(*angle_pose)
        return self._controller.send(
            Set.ctrlr_coms_set_home_pose,
            pack(CTRLR_GET_SET_HOME_POSE_PACK_UNPACK_FORMAT, *angle_pose)
        )

    def simple_joystick(
        self,
        coordinate_system: CoordinateSystem = None
    ) -> bool:
        """
        Простой графический интерфейс для режима 'TCP JOGGING', основанный на
        функции 'jog_once'. Для работы с пользовательской СК необходимо
        передать ее в качестве аргумента. Функция является блокирующей. Для
        выхода из функции и продолжения исполнения программы необходимо закрыть
        пользовательский интерфейс.

        Args:
            coordinate_system: Пользовательская система координат.
        Returns:
            True: По завершении работы функции.
        """

        SimpleJoystickUI(
            self.linear.jog_once,
            self.joint.jog_once,
            self.joint.set_jog_param_in_tcp,
            self.linear.get_actual_position,
            self.joint.get_actual_position,
            self.free_drive,
            self.mode.set,
            self.joint.add_new_waypoint,
            self.linear.add_new_offset,
            self.scale_setup.set,
            coordinate_system
        )
        return True

    def wait_waypoint_completion(
        self, waypoint_count: int = 0, await_sec: int = -1
    ) -> bool:
        """
        Ожидать завершения исполнения текущих заданных целевых точек.

        Args:
            waypoint_count: Количество точек в очереди, после которого можно
                продолжить исполнение программы.
            await_sec: Лимит времени ожидания.
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                условию).
        Returns:
            True: В случае успешного исполнения заданных точек.
            False: В случае таймаута (если await_sec >= 0).
        """

        validate_value(waypoint_count, WP_COUNT_LIMITS)
        waypoint_amount = 0
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            if waypoint_amount != self._rtd_receiver.rt_data.buff_fill:
                self._logger.debug(
                    (
                        f'Waypoint in queue: '
                        f'{self._rtd_receiver.rt_data.buff_fill}'
                    )
                )
                waypoint_amount = self._rtd_receiver.rt_data.buff_fill
            if waypoint_count >= self._rtd_receiver.rt_data.buff_fill:
                self._logger.debug('Waypoint queue is empty')
                return True
        return False
