from enum import IntEnum


class AddWayPointCommand(IntEnum):
    # command
    ctrlr_coms_move_add_wp: int = 1
    # motion types for waypoints
    move_wp_type_joint: int = 0
    move_wp_type_linear_cart: int = 1
    move_wp_type_tcp_pose: int = 2


class ControllerUnlockCommand(IntEnum):
    ctrlr_coms_unlock: int = 100


class JogModes(IntEnum):
    ctrlr_coms_jog_mode_off: int = 0
    ctrlr_coms_jog_mode_force: int = 1
    ctrlr_coms_jog_mode_velocity: int = 2
    ctrlr_coms_jog_mode_position: int = 3


class JointJogModes(IntEnum):
    ctrlr_coms_joint_jog_mode_off = 0
    ctrlr_coms_joint_jog_mode_on = 1


class Getters(IntEnum):
    ctrlr_coms_get_last_pos: int = 901
    ctrlr_coms_get_move_scale: int = 1115
    ctrlr_coms_get_gravity: int = 1116
    ctrlr_coms_get_zero_gravity_fscale: int = 1117
    ctrlr_coms_get_payload: int = 1121
    ctrlr_coms_get_tool: int = 1122
    ctrlr_coms_get_jog_param: int = 1123
    ctrlr_coms_get_force_param: int = 1124
    ctrlr_coms_get_tool_capsule_count: int = 1127
    ctrlr_coms_get_tool_capsule: int = 1128
    ctrlr_coms_get_link_capsule_count: int = 1129
    ctrlr_coms_get_link_capsule: int = 1130
    ctrlr_coms_get_home_pose: int = 1150
    ctrlr_coms_get_robot_view_info: int = 4000
    ctrlr_coms_get_sw_version: int = 3000
    ctrlr_coms_get_proto_version: int = 3001
    # get kinematics
    ctrlr_coms_fkine: int = 2000
    ctrlr_coms_ikine: int = 2001
    ctrlr_coms_ikine_optimal: int = 2002
    # io func
    ctrlr_coms_get_dig_input_func: int = 1132
    ctrlr_coms_get_dig_output_func: int = 1133
    ctrlr_coms_cbox_get_sfty_input_func: int = 1601


class Setters(IntEnum):
    ctrlr_coms_set_force_param: int = 1024
    ctrlr_coms_set_jog_param: int = 1023
    ctrlr_coms_set_home_pose: int = 1050
    ctrlr_coms_set_move_scale: int = 1015
    ctrlr_coms_set_gravity: int = 1016
    ctrlr_coms_set_outputs: int = 14
    ctrlr_coms_set_payload: int = 1021
    ctrlr_coms_store_settings: int = 1300
    ctrlr_coms_set_tool: int = 1022
    # io func
    ctrlr_coms_set_dig_input_func: int = 1032
    ctrlr_coms_set_dig_output_func: int = 1033
    # wrist func
    ctrlr_coms_set_wrist_io: int = 17
    ctrlr_coms_set_wrist_dig_input_func: int = 1053
    ctrlr_coms_set_wrist_dig_output_func: int = 1054
