from dataclasses import dataclass

from rc10_api.source.models.constants import (
    CTRLR_MAX_DIG_IN_BYTES,
    CTRLR_MAX_DIG_OUT_BYTES,
    CTRLR_MAX_AN_IN,
    CTRLR_MAX_AN_OUT,
    JOINTS_COUNT,
    PADDING_RES1_LENGTH,
    PADDING_RES2_LENGTH,
    TCP_POSITION_COUNT,
    WRIST_ACCEL,
    WRIST_GYRO,
    WRIST_MAX_AN_IN,
)

STRUCT_FORMAT = 'B7B2f 7d 4H 60d d2B 2Bf 10d 48d 5d 16B4d 16B4d 8B2f f I 6d 2f 6B 2B 6I 24d QQ f 4B'

@dataclass(order=True)
class RTD:
    packet_begin: float = 1  # package beginning check-byte (B)
    byte_res1: tuple = (
        PADDING_RES1_LENGTH  # padding for packet start, reserved values can be
    )
    # used for debug (7B)
    act_point: float = 1  # actual point (progress of current movement). From 0.0 to ?
    # `desired_point`. m or rad (f)
    desired_point: float = 1  # desired point (distance to be traveled to the next waypoint, m or
    # rad (f)

    cycle_time: float = 1  # actual cycle time (d)
    cycle_duty: float = 1  # time in % occupied by calculations (d)
    state: float = 1  # state of robot controller (d)
    safety: float = 1  # safety state of robot controller (d)
    servo_mode: float = 1  # mode of joint's servomotors (d)
    motion_mode: float = 1  # actual motion mode (d)
    jcond: float = 1  # Jacobi condition (d)

    buff_sz: float = 1  # waypoint ring buffer size (H)
    buff_fill: float = 1  # counter of accepted, but not completed yet
    # waypoints (H)
    wp_cntr: float = 1  # counter of all accepted waypoints (H)
    res: float = 1  # reserved (H)

    move_des_q: tuple = JOINTS_COUNT  # traj. gen. desired position for joint
    # space (6d)
    move_des_qd: tuple = JOINTS_COUNT  # traj. gen. desired velocity for joint
    # space (6d)
    move_des_tcp_x: tuple = JOINTS_COUNT  # traj. gen. desired position for cart.
    # space (6d)
    move_des_tcp_xd: tuple = JOINTS_COUNT  # traj. gen. desired velocity for cart.
    # space (6d)
    act_q: tuple = JOINTS_COUNT  # actual positions of joints (6d)
    act_qd: tuple = JOINTS_COUNT  # actual vel. of joints (6d)
    act_tcp_x: tuple = JOINTS_COUNT  # actual cart. position of TCP XYZ, RPY (6d)
    act_flange_x: tuple = JOINTS_COUNT  # actual cart. position of flange (zero tool offset)
    # XYZ, RPY (6d)
    act_tcp_xd: tuple = JOINTS_COUNT  # act cart. vel. XYZ, RPY (6d)
    act_trq: tuple = JOINTS_COUNT  # actual joints torque (6d)

    act_vel_scale: float = 1  # actual velocity scale (from 0.0 to 1.0) (d)
    act_vel_limit_reason: float = 1  # reason of velocity limiting by applying
    # scale (0 - velocity is not limited) (B)
    state_flags: float = 1  # additional flags (look `ctrlr_warning_flags_t`) (B)

    byte_res2: tuple = PADDING_RES2_LENGTH  # padding to 8 (2B)
    float_res2: float = 1 # padding to 8 (f)

    payload_mass: float = 1  # payload mass (kg) (d)
    payload_com: tuple = TCP_POSITION_COUNT  # position of center of mass (related to end-effector),
    # (XYZ) (3d)
    tool_offset: tuple = JOINTS_COUNT  # position and orientation of tool (related to end-effector), # (XYZ, RPY) (6d)
    
    frict_trq: tuple = JOINTS_COUNT  # predicted friction torque (6d)
    ne_trq: tuple = JOINTS_COUNT  # predicted gravity/coriolis (newton-euler
    # algorithm) torque (6d)
    act_force_e: tuple = JOINTS_COUNT  # actual force(XYZ)/torque(RPY) applied
    # to TCP in TCP coordinate frame (6d)
    act_force_0: tuple = JOINTS_COUNT  # the same in base coordinate frame (6d)
    des_trq: tuple = JOINTS_COUNT  # current command for servomotors (6d)
    des_qd: tuple = JOINTS_COUNT  # velocity command for servomotors (6d)
    des_amp: tuple = JOINTS_COUNT  # desired current (6d)
    des_iwin: tuple = JOINTS_COUNT  # possible difference between des_iq and
    # act_iq (6d)

    arm_current: float = 1  # (d)
    arm_voltage: float = 1  # (d)
    io_current: float = 1  # maximal of currents, provided to IO (d)
    psu_voltage: float = 1  # power supply unit voltage (Volts) (d)
    cbox_temp: float = 1  # maximal of temperatures inside of robot
    # controller (d)

    dig_in_count: float = 1  # number of bits (B)
    an_in_count: float = 1  # number of `double` values (analog inputs)(B)
    dig_in: tuple = CTRLR_MAX_DIG_IN_BYTES  # digital input values, packed in bytes (8B)
    an_in_curr_mode: tuple = CTRLR_MAX_AN_IN  # modes for analog inputs(4B)
    res_bytes: tuple = 2  # padding (2B)    
    an_in_value: tuple = CTRLR_MAX_AN_IN  # values of voltage/current on analog inputs (4d)
    
    dig_out_count: float = 1  # number of bits (digital outputs) (B)
    an_out_count: float = 1  # number of `double` values (analog outputs) (B)
    dig_out: tuple = CTRLR_MAX_DIG_OUT_BYTES  # digital output values, packed in bytes (8B)
    an_out_curr_mode: tuple = CTRLR_MAX_AN_OUT  # modes for analog outputs (4B)
    res_bytes2: tuple = 2  # padding (2B)
    an_out_value: tuple = CTRLR_MAX_AN_OUT  # values of voltage/current on analog outputs (4d)
    
    # WIRST
    wrist_dig_in_count: float = 1  # number of bits (B)
    wrist_dig_in: float = 1  # digital input values, packed in single byte.
    # First two inputs are buttons (B)
    wrist_dig_out_count: float = 1  # number of bits (digital outputs) (B)
    wrist_dig_out: float = 1  # digital output values, packed in single byte (B)
    wrist_an_in_count: float = 1  # number of `double` values (analog inputs)(B)
    wrist_an_in_curr_mode: tuple = WRIST_MAX_AN_IN  # modes for analog inputs (2B)
    wrist_mode: float = 1  # mode of board - see `tool_mode_t` (B)
    wrist_an_in_value: tuple = WRIST_MAX_AN_IN  # (2f)
    
    wrist_temperature: float = 1  # maximum of temperatures on circuit (CPU, MEMS) (f)
    
    wrist_safety_flags: float = 1  # safety flags (L)
    
    wrist_accel: tuple = WRIST_ACCEL  # accelerometer values (XYZ)(3d)
    wrist_gyro: tuple = WRIST_GYRO  # gyroscope values (XYZ)(3d)
    
    tool_dig_out_current: float = 1  # real current of do pins on tool connector (f)
    tool_power_current: float = 1  # real current of power on tool connector (f)

    joint_state: tuple = JOINTS_COUNT  # 0 - joint brakes applied, 1 - joint
    # brakes released (6B)
    res_bytes3: tuple = 2  # padding (2B)
    joint_err_state: tuple = JOINTS_COUNT  # error state of motors (6L)
    joint_volt: tuple = JOINTS_COUNT  # actual voltage of motors (Volts) (6d)
    joint_amp: tuple = JOINTS_COUNT  # actual currents of motors (Amperes) (6d)
    joint_temp_motor: tuple = JOINTS_COUNT  # actual temperatures of motors
    # (deg. Celsius) (6d)
    joint_temp_board: tuple = JOINTS_COUNT  # actual temperatures of motor
    # electronics (deg. Celsius) (6d)

    sec: float = 1  # timestamp's seconds (Q)
    nsec: float = 1  # timestamp's nanoseconds (Q)

    dist_to_blend: float = 1  # distance to blend left until blend between waypoints will start (f)
    
    byte_res3: tuple = 3  # padding for packet end, can be used for debug values (3B)
    packet_end: float = 1  # package ending check-byte (B)


@dataclass(frozen=True)
class RTDataPackageBorders:
    rtd_packet_begin: int = 0x12  # package beginning check-byte
    rtd_packet_end: int = 0x21  # package ending check-byte
