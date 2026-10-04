from __future__ import annotations
from struct import pack
from typing import TYPE_CHECKING

import rc10_api.source.features.mathematics.unit_convert as unit_c
from rc10_api.source.features.tools import (
    dataclass_to_tuple, set_position_orientation_units
)
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.mathematics.coordinate_system import (
    convert_position_orientation
)
from rc10_api.source.models.classes.data_classes.command_templates import (
    InverseKinematicOptimalTemplate, MOTION_SETUP
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Getters as Get
)
from rc10_api.source.models.constants import (
    CTRLR_IKINE_CMD_PACK_FORMAT, CTRLR_IKINE_CMD_UNPACK_FORMAT,
    CTRLR_FKINE_CMD_PACK_FORMAT, CTRLR_FKINE_CMD_UNPACK_FORMAT,
    CTRLR_IKINE_OPTIMAL_CMD_PACK_FORMAT, CTRLR_IKINE_OPTIMAL_CMD_UNPACK_FORMAT,
    FKINE_IKINE_RESPONSE_JOINT_POSITION_SLICE, FKINE_SOLUTIONS_COUNT,
    JOINT_COUNT, ORIENTATION_SLICE, POSITION_ORIENTATION_LENGTH,
    POSITION_SLICE, PREVIOUS_FKINE_SOLUTION_OFFSET, RESPONSE_CODE_OFFSET
)
from rc10_api.source.models.type_aliases import AngleUnits, PositionOrientation

if TYPE_CHECKING:
    from rc10_api.source.ap_interface.motion.coordinate_system import (
        CoordinateSystem
    )
    from rc10_api.source.ap_interface.motion.joint_motion import JointMotion
    from rc10_api.source.core.network.controller_socket import Controller


validate_length = validation.validate_length
validate_literal = validation.validate_literal


class Kinematics:
    """
    Класс для получения решения прямой и обратной задач кинематики.
    """

    _controller: Controller
    _joint: JointMotion

    def __init__(self, controller: Controller, joint: JointMotion) -> None:

        self._controller = controller
        self._joint = joint

    def get_forward(
        self,
        angle_pose: PositionOrientation,
        units: AngleUnits = None,
        coordinate_system: CoordinateSystem = None
    ) -> PositionOrientation | None:
        """
        Получить решение прямой задачи кинематики в пользовательской системе
        координат. Если система координат не была выбрана, то будет
        использована система координат основания робота.

        Args:
            joints_angles: 6 углов поворота моторов, от основания до фланца
                робота ('units').
            units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
            coordinate_system: Выбранная система координат. По-умолчанию
                используется система координат основания робота.

        Returns:
            list: Позиция ЦТИ в выбранной системе координат
                в формате (X, Y, Z, Rx, Ry, Rz), где (X, Y, Z) — м,
                (Rx, Ry,Rz) — 'units'
            None: В случае ошибки в расчетах в контроллере.
        """

        if units is None:
            units = MOTION_SETUP.units
        validate_literal('angle', units)
        validate_length(angle_pose, JOINT_COUNT)
        if units == 'deg':
            angle_pose = unit_c.degrees_to_radians(*angle_pose)
        self._controller.send(
            Get.ctrlr_coms_fkine,
            pack(CTRLR_FKINE_CMD_PACK_FORMAT, *angle_pose)
        )
        response = self._controller.receive(
            Get.ctrlr_coms_fkine, CTRLR_FKINE_CMD_UNPACK_FORMAT
        )
        tcp_pose = (
            list(response[FKINE_IKINE_RESPONSE_JOINT_POSITION_SLICE])
        )
        if response and response[0] == 0:
            if coordinate_system:
                tcp_pose = convert_position_orientation(
                    coordinate_system,
                    tcp_pose,
                    orientation_units='rad',
                    to_local=True
                )
            return (
                tcp_pose[POSITION_SLICE]
                + unit_c.radians_to_degrees(
                    *tcp_pose[ORIENTATION_SLICE]
                )
            ) if units == 'deg' else tcp_pose

    def get_inverse(
        self,
        tcp_pose: PositionOrientation,
        angle_pose: PositionOrientation = None,
        orientation_units: AngleUnits = None,
        get_all: bool = False,
    ) -> PositionOrientation | None:
        """
        Получить решение обратной задачи кинематики. Конвертация позиции и
        ориентации из локальной (пользовательской) в глобальную производится
        при передаче аргументов с помощью функции
        convert_position_orientation, переданные при этом единицы измерения
        должны совпадать с единицами измерения данного метода.

        Args:
            tcp_pose: Позиция и ориентация ЦТИ в глобальной
                системе координат (система координат основания робота) в
                формате:
                (X, Y, Z, Rx, Ry, Rz), где (X, Y, Z) — м,
                (Rx, Ry,Rz) — 'orientation_units'.
            angle_pose: Положение углов поворота моторов, относительно которого
                будет рассчитано ближайшее решение обратной задачи кинематики.
                По-умолчанию текущее значение, полученное из RTD.
            orientation_units: Единицы измерения. По-умолчанию градусы.
                'deg' — градусы.
                'rad' — радианы.
            get_all: Получить ли все решения или только оптимальное.
        Returns:
            PositionOrientation: Оптимальное решение задачи.
            Tuple[PositionOrientation, ...]: 8 решений задачи в формате 6
                углов поворотов моторов, от основания до фланца робота
                ('units').
            None: В случае ошибки в расчетах в контроллере.
        """
        if orientation_units is None:
            orientation_units = MOTION_SETUP.units
        if angle_pose is None:
            angle_pose = self._joint._rtd_receiver.rt_data.act_q
        validate_literal('angle', orientation_units)
        validate_length(
            tcp_pose, POSITION_ORIENTATION_LENGTH
        )
        validate_length(
            angle_pose, POSITION_ORIENTATION_LENGTH
        )
        tcp_pose = set_position_orientation_units(
            tcp_pose, orientation_units
        )
        if get_all:
            self._controller.send(
                Get.ctrlr_coms_ikine,
                pack(CTRLR_IKINE_CMD_PACK_FORMAT, *tcp_pose)
            )
            response = self._controller.receive(
                Get.ctrlr_coms_ikine, CTRLR_IKINE_CMD_UNPACK_FORMAT
            )
            if orientation_units == 'deg':
                response = unit_c.radians_to_degrees(*response)
            return tuple(
                response[
                    i * POSITION_ORIENTATION_LENGTH + RESPONSE_CODE_OFFSET:
                    i * POSITION_ORIENTATION_LENGTH
                    + PREVIOUS_FKINE_SOLUTION_OFFSET
                ] for i in range(FKINE_SOLUTIONS_COUNT)
            )
        ikine_template = InverseKinematicOptimalTemplate(
            target=tcp_pose,
            base_q=angle_pose
        )
        self._controller.send(
            Get.ctrlr_coms_ikine_optimal,
            pack(
                CTRLR_IKINE_OPTIMAL_CMD_PACK_FORMAT,
                *dataclass_to_tuple(ikine_template)
            )
        )
        response = self._controller.receive(
            Get.ctrlr_coms_ikine_optimal, CTRLR_IKINE_OPTIMAL_CMD_UNPACK_FORMAT
        )
        inverse_solution = (
            list(response[FKINE_IKINE_RESPONSE_JOINT_POSITION_SLICE])
        )
        if response and response[0] == 0:
            if orientation_units == 'deg':
                inverse_solution = unit_c.radians_to_degrees(*inverse_solution)
            return inverse_solution
        return None
