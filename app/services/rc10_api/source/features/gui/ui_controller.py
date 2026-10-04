from __future__ import annotations
from tkinter import END, Tk
from typing import TYPE_CHECKING

from rc10_api.source.ap_interface.motion.coordinate_system import CoordinateSystem
from rc10_api.source.features.gui.view import _WindowUI
from rc10_api.source.features.gui.bindings import Binding
from rc10_api.source.features.mathematics.coordinate_system import (
    convert_position_orientation
)
from rc10_api.source.models.classes.enum_classes.various_types import (
    JogParamInTCP
)
from rc10_api.source.models.classes.data_classes.command_templates import (
    MOTION_SETUP
)
from rc10_api.source.models.classes.enum_classes.various_types import (
    AngleUnitTypes, GUICoordinateSystem, MotionTypes
)
from rc10_api.source.models.constants import (
    JOYSTICK_ACCEL_MAX_DEG_SEC, JOYSTICK_ACCEL_MAX_RAD_SEC, JOINTS_COUNT,
    JOYSTICK_SPEED_MAX_DEG_SEC, JOYSTICK_SPEED_MAX_RAD_SEC,
)

if TYPE_CHECKING:
    from rc10_api.source.ap_interface.motion.linear_motion import LinearMotion
    from rc10_api.source.ap_interface.motion.joint_motion import JointMotion
    from rc10_api.source.ap_interface.motion.motion_host import Motion
    from rc10_api.source.ap_interface.motion.motion_mode import MotionMode
    from rc10_api.source.ap_interface.motion.move_scaling import MoveScaling


class SimpleJoystickUI(Tk):
    def __init__(
        self,
        linear_jog_func: LinearMotion.jog_once,
        joint_jog_func: JointMotion.jog_once,
        joint_set_jog_param_in_tcp: JointMotion.set_jog_param_in_tcp,
        act_linear_pose: LinearMotion.get_actual_position,
        act_joint_pose: JointMotion.get_actual_position,
        free_drive: Motion.free_drive,
        mode_set_func: MotionMode.set,
        add_new_waypoint: JointMotion.add_new_waypoint,
        add_new_offset: LinearMotion.add_new_offset,
        scale_setup: MoveScaling.set,
        coordinate_system: CoordinateSystem | None
    ):
        super().__init__()
        self.ui = _WindowUI(self, coordinate_system)
        self.act_l_pose = act_linear_pose
        self.act_j_pose = act_joint_pose
        self.joint_set_jog_param_in_tcp = joint_set_jog_param_in_tcp
        self.mode_set = mode_set_func
        self.add_new_waypoint = add_new_waypoint
        self.add_new_offset = add_new_offset
        self.scale_setup = scale_setup
        self.units = MOTION_SETUP.units
        self.coordinate_system = coordinate_system
        self.current_coordinate_system = (
            self.ui.coordinate_system_combobox.get()
        )
        self.jog_buttons = {
            self.ui.x_min_btn: (linear_jog_func,  'x_min', 'X', '-'),

            # self.ui.x_min_btn: (linear_jog_func,  'y_min', 'Y', '-'),

            self.ui.x_max_btn: (linear_jog_func, 'x_max', 'X', '+'),
            self.ui.y_min_btn: (linear_jog_func, 'y_min', 'Y', '-'),
            self.ui.y_max_btn: (linear_jog_func, 'y_max', 'Y', '+'),
            self.ui.z_min_btn: (linear_jog_func, 'z_min', 'Z', '-'),
            self.ui.z_max_btn: (linear_jog_func, 'z_max', 'Z', '+'),
            self.ui.rx_min_btn: (linear_jog_func, 'rx_min', 'Rx', '-'),
            self.ui.rx_max_btn: (linear_jog_func, 'rx_max', 'Rx', '+'),
            self.ui.ry_min_btn: (linear_jog_func, 'ry_min', 'Ry', '-'),
            self.ui.ry_max_btn: (linear_jog_func, 'ry_max', 'Ry', '+'),
            self.ui.rz_min_btn: (linear_jog_func, 'rz_min', 'Rz', '-'),
            self.ui.rz_max_btn: (linear_jog_func, 'rz_max', 'Rz', '+'),
            self.ui.j0_min_btn: (joint_jog_func, 'j0_min', 0, '-'),
            self.ui.j0_max_btn: (joint_jog_func, 'j0_max', 0, '+'),
            self.ui.j1_min_btn: (joint_jog_func, 'j1_mix', 1, '-'),
            self.ui.j1_max_btn: (joint_jog_func, 'j1_max', 1, '+'),
            self.ui.j2_min_btn: (joint_jog_func, 'j2_mix', 2, '-'),
            self.ui.j2_max_btn: (joint_jog_func, 'j2_max', 2, '+'),
            self.ui.j3_min_btn: (joint_jog_func, 'j3_mix', 3, '-'),
            self.ui.j3_max_btn: (joint_jog_func, 'j3_max', 3, '+'),
            self.ui.j4_min_btn: (joint_jog_func, 'j4_mix', 4, '-'),
            self.ui.j4_max_btn: (joint_jog_func, 'j4_max', 4, '+'),
            self.ui.j5_min_btn: (joint_jog_func, 'j5_mix', 5, '-'),
            self.ui.j5_max_btn: (joint_jog_func, 'j5_max', 5, '+'),
        }
        self.binds = []
        self.binds.append(Binding('empty', None))
        for (
            button, (func, name, axis, direction)
         ) in self.jog_buttons.items():
            self.binds.append(
                Binding(
                    name,
                    button.connect(func, axis, direction)
                )
            )
            self.binds.append(
                Binding(
                    name,
                    button.connect_release(self.stop)
                )
            )
        for group in self.ui.rtd_groups:
            sequence_str = (
                'ctrl_j_c' if group.type_ == MotionTypes.JOINT else 'ctrl_l_c'
            )
            self.binds.append(
                Binding(
                    sequence_str,
                    group.copy_btn.connect(self.copy_rtd, group.type_)
                )
            )
            if group.paste_btn is not None:
                group.paste_btn.connect(self.paste_copied_data)
        self.binds.append(
            Binding(
                'move',
                self.ui.move_btn.connect(self.move)
            )
        )
        self.binds.append(
            Binding(
                'move',
                self.ui.move_btn.connect_release(self.stop)
            )
        )
        self.binds.append(
            Binding(
                'offset',
                self.ui.shift_btn.connect(self.shift)
            )
        )
        self.binds.append(
            Binding(
                'offset',
                self.ui.shift_btn.connect_release(self.stop)
            )
        )
        self.binds.append(
            Binding(
                'free_drive',
                self.ui.free_drive_btn.connect(free_drive)
            )
        )
        self.ui.free_drive_switch.bind(
            '<ButtonRelease>', self.set_free_drive
        )
        self.ui.coordinate_system_combobox.bind(
            '<<ComboboxSelected>>', self.set_current_coordinate_system
        )
        self.ui.orientation_units_combobox.bind(
            '<<ComboboxSelected>>', self.set_orientation_units_combobox_value
        )
        self.ui.speed_scale.bind(
            '<ButtonRelease-1>', self.set_speed_scale_value
        )
        self.task = self.after(100, self.update_rtd)
        self.protocol('WM_DELETE_WINDOW', self.close_window)
        if self.units == 'rad':
            self.ui.orientation_units_combobox.set(AngleUnitTypes.RAD)
        scale_setup(
            velocity=self.ui.speed_scale.get(),
            acceleration=self.ui.speed_scale.get()
        )
        self.mainloop()

    def copy_rtd(self, type_: str):
        self.clipboard_clear()
        self.clipboard_append(
            str(self.act_j_pose())
            if type_ == MotionTypes.JOINT else str(self.act_l_pose(self.units))
        )

    def set_current_coordinate_system(self, event):
        self.current_coordinate_system = (
            self.ui.coordinate_system_combobox.get()
        )
        if self.current_coordinate_system == GUICoordinateSystem.CTI:
            self.joint_set_jog_param_in_tcp(JogParamInTCP.TRUE)
        else:
            self.joint_set_jog_param_in_tcp(JogParamInTCP.FALSE)

    def set_free_drive(self, event):
        checkbox_value = self.ui.enabled.get()
        if checkbox_value == 1:
            self.ui.free_drive_btn.set_pressed()
        else:
            self.ui.free_drive_btn.set_released()

    def set_orientation_units_combobox_value(self, event):
        self.units = (
            'deg'
            if self.ui.orientation_units_combobox.get() == AngleUnitTypes.DEG
            else 'rad'
        )

    def set_speed_scale_value(self, event):
        scale_value = self.ui.speed_scale.get()
        self.scale_setup(
            velocity=scale_value, acceleration=scale_value
        )

    def get_entry_data(self, motion_type):
        entry_group = (
            self.ui.move_entry_group
            if motion_type == MotionTypes.JOINT
            else self.ui.offset_entry_group
        )
        return [float(entry.get()) for entry in entry_group.entries]

    def move(self):
        tcp_pose = self.get_entry_data(MotionTypes.JOINT)
        if self.current_coordinate_system == GUICoordinateSystem.LOCAL:
            tcp_pose = convert_position_orientation(
                coordinate_system=self.coordinate_system,
                position_orientation=tcp_pose,
                orientation_units=self.units
            )
        speed, accel = (
            JOYSTICK_SPEED_MAX_DEG_SEC, JOYSTICK_ACCEL_MAX_DEG_SEC
        ) if self.units == 'deg' else (
            JOYSTICK_SPEED_MAX_RAD_SEC, JOYSTICK_ACCEL_MAX_RAD_SEC
        )
        self.add_new_waypoint(
            tcp_pose=tcp_pose,
            speed=speed,
            accel=accel,
            units=self.units
        )
        self.mode_set('move')

    def paste_copied_data(self):
        clipboard = [
            data.strip() for data
            in self.clipboard_get().strip('[]').split(',')
        ]
        entry = self.ui.move_entry_group.entries
        if len(clipboard) == JOINTS_COUNT:
            for id, entry in enumerate(self.ui.move_entry_group.entries):
                entry.delete(0, END)
                entry.insert(0, clipboard[id])

    def shift(self):
        act_l_pose = self.act_l_pose(self.units)
        if self.current_coordinate_system == GUICoordinateSystem.LOCAL:
            act_l_pose = convert_position_orientation(
                coordinate_system=self.coordinate_system,
                position_orientation=act_l_pose,
                orientation_units=self.units,
                to_local=True
            )
        self.add_new_offset(
            waypoint=act_l_pose,
            offset=self.get_entry_data(MotionTypes.LINEAR),
            coordinate_system=(
                self.coordinate_system
                if self.current_coordinate_system == GUICoordinateSystem.LOCAL
                else None
            ),
            orientation_units=self.units
        )
        self.mode_set('move')

    def stop(self):
        self.mode_set('hold')

    def update_rtd(self):
        act_l_pose = self.act_l_pose(self.units)
        if self.current_coordinate_system == GUICoordinateSystem.LOCAL:
            act_l_pose = convert_position_orientation(
                coordinate_system=self.coordinate_system,
                position_orientation=act_l_pose,
                orientation_units=self.units,
                to_local=True
            )
        elif self.current_coordinate_system == GUICoordinateSystem.CTI:
            act_l_pose = [0] * 6
        for group in self.ui.rtd_groups:
            pose = (
                self.act_j_pose(self.units)
                if group.type_ == MotionTypes.JOINT else act_l_pose
            )
            for i in range(len(group.labels)):
                group.labels[i].config(text=str(round(pose[i], 5)))
        self.task = self.after(50, self.update_rtd)

    def release_all(self):
        for binding in self.binds:
            if binding.button and binding.button.is_pressed():
                binding.button.set_released(None)

    def close_window(self):
        self.after_cancel(self.task)
        self.destroy()
