from __future__ import annotations
from threading import main_thread
from time import sleep
from typing import TYPE_CHECKING

from rc10_api.source.core.exceptions.status_error.controller_state_error import (
    ControllerFailureError
)
from rc10_api.source.core.exceptions.status_error.safety_status_error import (
    EmergencyStopError, SafetyViolationError, ControllerFaultError
)
from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver
from rc10_api.source.models.classes.enum_classes.state_classes import (
    InComingControllerState as Ics,
    InComingMotionMode as Imm,
    InComingSafetyStatus as Iss,
    WristMode as Wm,
    MotionWarning as Mw
)
if TYPE_CHECKING:
    from logging import Logger


class StateHandler:
    _rtd_receiver: RTDReceiver
    _logger: Logger

    def __init__(
        self,
        rtd_receiver: RTDReceiver,
        logger: Logger,
        ignore_exceptions: bool
    ):
        super().__init__()

        self._rtd_receiver = rtd_receiver
        self._logger = logger
        self._ignore_exceptions = ignore_exceptions
        self._is_active = True
        self._controller_state = -1
        self._motion_mode = -1
        self._safety_status = -1
        self._safety_warning = False
        self._controller_warning = False
        self._wrist_mode = -1

    def start(self):
        while self.get_active() and main_thread().is_alive():
            if self._ignore_exceptions:
                try:
                    self.check_all()
                except (
                    ControllerFailureError,
                    ControllerFaultError,
                    EmergencyStopError,
                    SafetyViolationError
                ):
                    pass
            else:
                self.check_all()
            sleep(0.01)

    def check_all(self):
        self.check_controller_state()
        self.check_motion_mode()
        self.check_safety_status()
        self.check_wrist_mode()

    def check_wrist_mode(self):
        if self._rtd_receiver.rt_data.wrist_mode != self._wrist_mode:
            self._logger.info(
                f'Robot wrist-mode: '
                f'{Wm(int(self._rtd_receiver.rt_data.wrist_mode)).name}'
            )
            self._wrist_mode = self._rtd_receiver.rt_data.wrist_mode

    def check_motion_mode(self):
        if self._rtd_receiver.rt_data.motion_mode != self._motion_mode:
            self._logger.info(
                f'Robot motion-mode: '
                f'{Imm(int(self._rtd_receiver.rt_data.motion_mode)).name}'
            )
            self._motion_mode = self._rtd_receiver.rt_data.motion_mode
            if self._motion_mode == Imm.pause:
                if self._rtd_receiver.rt_data.state_flags:
                    self._logger.warning(
                        "Robot motion warning:" + Mw(int(
                            self._rtd_receiver.rt_data.state_flags
                        )).name
                    )

    def check_controller_state(self):
        if self._rtd_receiver.rt_data.state != self._controller_state:
            state = int(self._rtd_receiver.rt_data.state)
            if self._controller_state != -1:
                self._logger.info(f'Robot controller-state: {Ics(state).name}')
            if state == Ics.failure:
                if self._controller_state == -1:
                    if self._controller_warning:
                        return
                    else:
                        self._controller_warning = True
                        return self._logger.warning(
                            'Controller inner error happened. '
                            'Controller reboot needed.'
                        )
                else:
                    raise ControllerFailureError
            if self._controller_warning:
                self._controller_warning = False
            self._controller_state = self._rtd_receiver.rt_data.state

    def check_safety_status(self):
        if self._rtd_receiver.rt_data.safety != self._safety_status:
            status = int(self._rtd_receiver.rt_data.safety)
            match status:
                case Iss.emergency_stop:
                    if self._safety_status == -1:
                        if self._safety_warning:
                            return
                        else:
                            self._safety_warning = True
                            return self._logger.warning(
                                'Robot emergency stop (1-category stop event)'
                            )
                    else:
                        raise EmergencyStopError
                case Iss.fault:
                    if self._safety_status == -1:
                        if self._safety_warning:
                            return
                        else:
                            self._safety_warning = True
                            return self._logger.warning(
                                'Robot software fault (0-category stop event).'
                                ' Check core log-files'
                            )
                    else:
                        raise ControllerFaultError
                case Iss.violation:
                    if self._safety_status == -1:
                        if self._safety_warning:
                            return
                        else:
                            self._safety_warning = True
                            return self._logger.warning(
                                'Robot safety violation '
                                '(0-category stop event)'
                            )
                    else:
                        raise SafetyViolationError
            if self._safety_warning:
                self._safety_warning = False
            self._logger.info(f'Robot safety-status: {Iss(status).name}')
            self._safety_status = self._rtd_receiver.rt_data.safety

    def shutdown(self):
        self.set_active(False)

    def get_active(self) -> bool:
        return self._is_active

    def set_active(self, state: bool):
        self._is_active = state
