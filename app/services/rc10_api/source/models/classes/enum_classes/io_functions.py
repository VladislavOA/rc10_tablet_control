from rc10_api.source.models.classes.enum_classes.base_int_enum import BaseIntEnum


class InputFunction(BaseIntEnum):
    no_func: int = 0
    move: int = 1
    hold: int = 2
    pause: int = 3
    zero_gravity: int = 4
    run: int = 5
    move_to_home: int = 6
    ifunc_hold_io_dig_output: int = 200
    ifunc_trigger_io_dig_output: int = 300


class OutputFunction(BaseIntEnum):
    no_func: int = 0
    no_move_signal_false: int = 1
    no_move_signal_true: int = 2
    move_status_signal_true_false: int = 3
    run_signal_true: int = 4
    warning_signal_true: int = 5
    error_signal_true: int = 6


class SafetyInputFunctions(BaseIntEnum):
    di_type_input: int = 0
    di_type_emcy_input_stop_0_nc: int = 1
    di_type_emcy_input_stop_1_nc: int = 2
    di_type_sfgrd_stop_nc: int = 3
    di_type_sfgrd_release_no: int = 4
