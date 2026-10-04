from __future__ import annotations
from typing import TYPE_CHECKING

from rc10_api.source.ap_interface.io.analog_io import AnalogIO
from rc10_api.source.ap_interface.io.digital_io import DigitalIO

if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver
    from rc10_api.source.core.network.controller_socket import Controller


class IO:

    digital: DigitalIO
    analog: AnalogIO

    def __init__(
        self, controller: Controller, rtd_receiver: RTDReceiver, logger: Logger
    ) -> None:

        self.digital = DigitalIO(controller, rtd_receiver, logger)
        self.analog = AnalogIO(controller, rtd_receiver, logger)
