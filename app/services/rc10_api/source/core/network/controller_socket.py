from __future__ import annotations
import struct
import time
from typing import TYPE_CHECKING, Any

from rc10_api.source.core.exceptions.data_validation_error.parsing_error import (
    CommandTypeError, CorruptedPackageError)
from rc10_api.source.core.network.socket_factory import SocketWrapper
from rc10_api.source.models.constants import (
    CMD_PORT, CTRLR_CMD_PAYLOAD_LENGTH_SIZE, CTRLR_CMD_TYPE_LENGTH,
    EMPTY_BYTES, CTRLR_CMD_DATA_PACK_UNPACK_FORMAT
)

if TYPE_CHECKING:
    from logging import Logger


class Controller(SocketWrapper):
    def __init__(self, ip: str, timeout: int, logger: Logger):
        SocketWrapper.__init__(self, ip, CMD_PORT, timeout)
        self._logger = logger

    def receive(
        self, command_type: int, struct_format: str
    ) -> tuple[Any, ...]:
        data = self.recv_(CTRLR_CMD_PAYLOAD_LENGTH_SIZE)
        package_size = struct.unpack(CTRLR_CMD_DATA_PACK_UNPACK_FORMAT, data)
        if package_size[0] < CTRLR_CMD_PAYLOAD_LENGTH_SIZE:
            raise CorruptedPackageError
        data = self.recv_(CTRLR_CMD_TYPE_LENGTH)
        received_command_type = struct.unpack(
            CTRLR_CMD_DATA_PACK_UNPACK_FORMAT, data
        )
        self._logger.debug(
            f'Received response command-type: {received_command_type[0]}'
        )
        if received_command_type[0] != command_type:
            raise CommandTypeError
        data = self.recv_(package_size[0] - CTRLR_CMD_PAYLOAD_LENGTH_SIZE)
        return struct.unpack(struct_format, data)

    def send(self, cmd_type: int, payload: bytes = EMPTY_BYTES) -> bool:
        # if cmd_type == 10:
        #     # byte_message = b'\x10\x00\x00\x00\n\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00'
        #     byte_message = b'\x10\x00\x00\x00\n\x00\x00\x00\x01\x00\x00\x00\x00\x00\x01\x01\xff\x01\x00\x00'

        # else:
        byte_message = struct.pack(
            CTRLR_CMD_DATA_PACK_UNPACK_FORMAT,
            len(payload) + CTRLR_CMD_PAYLOAD_LENGTH_SIZE
        ) + struct.pack(CTRLR_CMD_DATA_PACK_UNPACK_FORMAT, cmd_type)
        if len(payload) > 0:
            byte_message = byte_message + payload
            
        super().send(byte_message)
        # self._logger.debug(f'Sent command-type: {cmd_type}')
        return True

    def initialise(self) -> bool:
        self.create_connection()
        time.sleep(1)
        return True
