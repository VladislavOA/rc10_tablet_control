import socket

from rc10_api.source.core.exceptions.connection_error import (
    BrokenConnectionError, ClientDisconnectedError, EmptyPackageError,
    ServerConnectionError
)
from rc10_api.source.models.constants import EMPTY_BYTES


class SocketWrapper:

    def __init__(self, ip: str, port: int, timeout: int):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.socket: socket.socket | None = None
        self._is_active = False

    def create_connection(self) -> bool:
        try:
            self.socket = socket.create_connection(
                address=(self.ip, self.port), timeout=self.timeout
            )
            self.set_active(True)
        except Exception as e:
            raise ServerConnectionError(self.port) from e

        return True

    def recv_(self, message_length: int) -> bytes:
        try:
            chunk = self.socket.recv(message_length)
            if chunk == EMPTY_BYTES:
                raise EmptyPackageError
            return chunk
        except Exception as e:
            raise ClientDisconnectedError(
                'Failed to receive package from server'
            ) from e

    def send(self, package: bytes):
        try:
            sent = self.socket.send(package)
            if sent == 0:
                raise BrokenConnectionError
        except Exception as e:
            raise ClientDisconnectedError(
                'Failed to send package to server'
            ) from e

    def shutdown(self):
        self.set_active(False)
        if self.socket:
            self.socket.close()

    def get_active(self) -> bool:
        return self._is_active

    def set_active(self, state: bool):
        self._is_active = state
