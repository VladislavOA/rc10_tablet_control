from __future__ import annotations
from struct import pack
from typing import TYPE_CHECKING, Callable

import rc10_api.source.features.mathematics.unit_convert as unit_c
from rc10_api.source.features.tools import set_position_orientation_units
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.mathematics.coordinate_system import (
    convert_position_orientation
)
from rc10_api.source.features.tools import dataclass_to_tuple, literal_to_int
from rc10_api.source.models.classes.data_classes.command_templates import (
    MOTION_SETUP, JogCommandTemplate, MoveCommandTemplate
)
from rc10_api.source.models.classes.enum_classes import state_classes
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    AddWayPointCommand as Awp, JogModes as Jm
)
from rc10_api.source.models.constants import (
    ACCEL_LIMITS, BLEND_LIMITS, JOG_CMD_PACK_FORMAT, ORIENTATION_SLICE,
    POSITION_ORIENTATION_LENGTH, POSITION_SLICE, SPEED_LIMITS
)
from rc10_api.source.models.type_aliases import (
    AngleUnits, JogAxis, JogDirection, PositionOrientation
)

if TYPE_CHECKING:
    from rc10_api.source.ap_interface.motion.coordinate_system import (
        CoordinateSystem
    )
    from rc10_api.source.core.network.controller_socket import Controller
    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver


Omm = state_classes.OutComingMotionMode
validate_length = validation.validate_length
validate_literal = validation.validate_literal
validate_value = validation.validate_value


class LinearMotion:
    """
    Класс для работы с линейным (декартовым) типом движения в формате
    (X, Y, Z, Rx, Ry, Rz), где (X, Y, Z) — м, (Rx, Ry,Rz) — углы поворотов
    (рад / град).
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
        tcp_pose: PositionOrientation,
        speed: float = None,
        accel: float = None,
        blend: float = None,
        orientation_units: AngleUnits = None,
    ) -> bool:
        """
        Добавить целевую точку типа движения 'Linear' в глобальной системе
        координат (система координат основания робота). Конвертация позиции и
        ориентации из локальной СК (пользовательской) в глобальную производится
        при передаче аргументов с помощью функции
        convert_position_orientation, переданные при этом единицы измерения
        должны совпадать с единицами измерения данного метода.

        Args:
            tcp_pose: Позиция ЦТИ в формате (X, Y, Z, Rx, Ry, Rz),
                где (X, Y, Z) — м, (Rx, Ry,Rz) — 'orientation_units'.
            speed: Скорость перемещения точки (0 - 3 м/с).
            accel: Ускорение перемещения точки (0 - 15 м/c^2).
            blend: Радиус сглаживания движения (м).
                (Радиус вокруг точки, при пересечении которого траекторией
                движения робота начинается/заканчивается сглаживание).
            orientation_units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
        Returns:
            True: В случае успешной отправки команды.
        """

        if speed is None:
            speed = MOTION_SETUP.linear_speed
        if accel is None:
            accel = MOTION_SETUP.linear_acceleration
        if blend is None:
            blend = MOTION_SETUP.blend
        if orientation_units is None:
            orientation_units = MOTION_SETUP.units
        validate_literal('angle', orientation_units)
        validate_length(tcp_pose, POSITION_ORIENTATION_LENGTH)
        validate_value(blend, BLEND_LIMITS)
        validate_value(speed, SPEED_LIMITS)
        validate_value(accel, ACCEL_LIMITS)
        tcp_pose = set_position_orientation_units(
            tcp_pose, orientation_units
        )
        command = MoveCommandTemplate(
            t=Awp.move_wp_type_linear_cart,
            des_x=tcp_pose,
            v_max_t=speed,
            v_max_r=speed,
            a_max_t=accel,
            a_max_r=accel,
            r_blend=blend
        )
        return self._add_waypoint(command)

    def add_new_offset(
        self,
        waypoint: PositionOrientation,
        offset: PositionOrientation,
        coordinate_system: CoordinateSystem = None,
        speed: float = None,
        accel: float = None,
        blend: float = None,
        orientation_units: AngleUnits = None,
    ) -> bool:
        """
        Добавить смещение offset относительно переданной точки waypoint.
        Для смещения в пользовательской системе координат необходимо передать
        данную СК в качестве аргумента метода.

        Args:
            waypoint: Точка, относительно которой добавляется смещение в
                формате (X, Y, Z, Rx, Ry, Rz)
            offset: Смещение относительно заданной точки в формате
                (X, Y, Z, Rx, Ry, Rz)
            coordinate_system: Выбранная система координат. По-умолчанию
                используется система координат основания робота.
            speed: Скорость перемещения точки (0 - 3 м/с).
            accel: Ускорение перемещения точки (0 - 15 м/c^2).
            blend: Радиус сглаживания движения (м).
                (Радиус вокруг точки, при пересечении которого траекторией
                движения робота начинается/заканчивается сглаживание).
            orientation_units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
        Returns:
            True: В случае успешной отправки команды.
        """

        if speed is None:
            speed = MOTION_SETUP.linear_speed
        if accel is None:
            accel = MOTION_SETUP.linear_acceleration
        if blend is None:
            blend = MOTION_SETUP.blend
        if orientation_units is None:
            orientation_units = MOTION_SETUP.units
        validate_literal('angle', orientation_units)
        for tcp_pose in (waypoint, offset):
            validate_length(tcp_pose, POSITION_ORIENTATION_LENGTH)
        validate_value(blend, BLEND_LIMITS)
        validate_value(speed, SPEED_LIMITS)
        validate_value(accel, ACCEL_LIMITS)
        new_tcp_pose = [
            waypoint_coordinate + offset_coordinate
            for waypoint_coordinate, offset_coordinate in zip(waypoint, offset)
        ]
        if coordinate_system:
            new_tcp_pose = convert_position_orientation(
                coordinate_system=coordinate_system,
                position_orientation=new_tcp_pose,
                orientation_units=orientation_units
            )
        new_tcp_pose = set_position_orientation_units(
            new_tcp_pose, orientation_units
        )
        command = MoveCommandTemplate(
            t=Awp.move_wp_type_linear_cart,
            des_x=new_tcp_pose,
            v_max_t=speed,
            v_max_r=speed,
            a_max_t=accel,
            a_max_r=accel,
            r_blend=blend
        )
        return self._add_waypoint(command)

    def get_actual_position(
        self,
        orientation_units: AngleUnits = None,
        coordinate_system: CoordinateSystem = None
    ) -> PositionOrientation | None:
        """
        Получить позицию и ориентацию ЦТИ в Linear формате
        (X, Y, Z, Rx, Ry, Rz), где (X, Y, Z) — м, (Rx, Ry,Rz) —
        'orientation_units', в системе координат пользователя. Если
        пользовательская система координат не была выбрана, то будет
        использована система координат основания робота. (Позиция и ориентация
        точки определяется тремя координатами положения ЦТИ и тремя углами
        поворотов вокруг осей).

        Args:
            orientation_units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
            coordinate_system: Выбранная система координат. По-умолчанию
                используется система координат основания робота.
        Returns:
            list: Позиция и ориентация ЦТИ в формате (X, Y, Z, Rx, Ry, Rz),
            где (X, Y, Z) — м, (Rx, Ry,Rz) — 'orientation_units'.
        """

        if orientation_units is None:
            orientation_units = MOTION_SETUP.units
        validate_literal('angle', orientation_units)
        if coordinate_system:
            actual_tcp_pose = convert_position_orientation(
                coordinate_system,
                self._rtd_receiver.rt_data.act_tcp_x,
                orientation_units='rad',
                to_local=True
            )
        else:
            actual_tcp_pose = list(
                self._rtd_receiver.rt_data.act_tcp_x
            )
        return (
            actual_tcp_pose[POSITION_SLICE]
            + unit_c.radians_to_degrees(
                *actual_tcp_pose[ORIENTATION_SLICE]
            )
        ) if orientation_units == 'deg' else actual_tcp_pose

    def jog_once(self, jog_axis: JogAxis, jog_direction: JogDirection) -> bool:
        """
        Режим 'TCP JOGGING'. Разовая команда кратковременного движения робота
        по осям. Команда является циклической. Для корректной работы режима
        необходимо вызывать метод в цикле, с
        частотой 100 Hz.

        Args:
            jog_axis: Ось перемещения (X, Y, Z, Rx, Ry, Rz).
            jog_direction: Направление перемещения вдоль оси.
                '+' — для перемещения в положительном направлении вдоль оси.
                '-' — для перемещения в отрицательном направлении вдоль оси.

        Returns:
            True: В случае успешной отправки команды.
        """

        validate_literal('axis', jog_axis)
        validate_literal('math', jog_direction)
        jog_template = JogCommandTemplate()
        jog_template.var[literal_to_int(jog_axis)] = (
            literal_to_int(jog_direction)
        )
        jog_template.mode = Jm.ctrlr_coms_jog_mode_velocity
        return (
            self._controller.send(
                Omm.jog,
                pack(
                    JOG_CMD_PACK_FORMAT,
                    *dataclass_to_tuple(jog_template)
                )
            )
        )
    
    def jog_once_all_axis(self, jog_directions: JogDirection) -> bool:
        """
        Режим 'TCP JOGGING'. Разовая команда кратковременного движения робота
        по осям. Команда является циклической. Для корректной работы режима
        необходимо вызывать метод в цикле, с
        частотой 100 Hz.

        Args:
            jog_direction: Направление перемещения вдоль оси.
                '+' — для перемещения в положительном направлении вдоль оси.
                '-' — для перемещения в отрицательном направлении вдоль оси.

        Returns:
            True: В случае успешной отправки команды.
        """
        axis = ["X", "Y", "Z", "Rx", "Ry", "Rz"]

        jog_template = JogCommandTemplate()

        for i, a in enumerate(axis):
            validate_literal('axis', a)
            if jog_directions[i] != "0":
                validate_literal('math', jog_directions[i])
                
                jog_template.var[literal_to_int(a)] = (
                    literal_to_int(jog_directions[i])
                )
        jog_template.mode = Jm.ctrlr_coms_jog_mode_velocity
        return (
            self._controller.send(
                Omm.jog,
                pack(
                    JOG_CMD_PACK_FORMAT,
                    *dataclass_to_tuple(jog_template)
                )
            )
        )
    
    # ТЕСТЫ СКРЫТЫХ ВОЗМОЖНОСТЕЙ
    # def jog_force(self, jog_directions: JogDirection, n) -> bool:
    #     """
    #     Режим 'TCP JOGGING'. Разовая команда кратковременного движения робота
    #     по осям. Команда является циклической. Для корректной работы режима
    #     необходимо вызывать метод в цикле, с
    #     частотой 100 Hz.

    #     Args:
    #         jog_direction: Направление перемещения вдоль оси.
    #             '+' — для перемещения в положительном направлении вдоль оси.
    #             '-' — для перемещения в отрицательном направлении вдоль оси.

    #     Returns:
    #         True: В случае успешной отправки команды.
    #     """
    #     axis = ["X", "Y", "Z", "Rx", "Ry", "Rz"]

    #     jog_template = JogCommandTemplate()

    #     for i, a in enumerate(axis):
    #         validate_literal('axis', a)
    #         if jog_directions[i] != "0":
    #             validate_literal('math', jog_directions[i])
                
    #             jog_template.force_const[literal_to_int(a)] = (
    #                 literal_to_int(jog_directions[i])
    #             )

    #             jog_template.force_en[literal_to_int(a)] = (
    #                 n[i]
    #             )
        
    #     jog_template.mode = Jm.ctrlr_coms_jog_mode_force
    #     return (
    #         self._controller.send(
    #             Omm.jog,
    #             pack(
    #                 JOG_CMD_PACK_FORMAT,
    #                 *dataclass_to_tuple(jog_template)
    #             )
    #         )
    #     )
    
    # def jog_pos(self, jog_directions: JogDirection) -> bool:
        """
        Режим 'TCP JOGGING'. Разовая команда кратковременного движения робота
        по осям. Команда является циклической. Для корректной работы режима
        необходимо вызывать метод в цикле, с
        частотой 100 Hz.

        Args:
            jog_direction: Направление перемещения вдоль оси.
                '+' — для перемещения в положительном направлении вдоль оси.
                '-' — для перемещения в отрицательном направлении вдоль оси.

        Returns:
            True: В случае успешной отправки команды.
        """
        axis = ["X", "Y", "Z", "Rx", "Ry", "Rz"]

        jog_template = JogCommandTemplate()

        for i, a in enumerate(axis):
            validate_literal('axis', a)
            if jog_directions[i] != "0":
                validate_literal('math', jog_directions[i])
                
                jog_template.var[literal_to_int(a)] = (
                    literal_to_int(jog_directions[i])
                )

                jog_template.stiff[literal_to_int(a)] = (
                    100
                )

                # jog_template.force_en[literal_to_int(a)] = (
                #     n[i]
                # )
        
        jog_template.mode = Jm.ctrlr_coms_jog_mode_position
        return (
            self._controller.send(
                Omm.jog,
                pack(
                    JOG_CMD_PACK_FORMAT,
                    *dataclass_to_tuple(jog_template)
                )
            )
        )
