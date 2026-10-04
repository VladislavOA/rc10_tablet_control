from dataclasses import dataclass


@dataclass
class Version:
    """
    Версия rc10_api. Создается из версии ПО ядра, протокола ядра и версии ПО rc10_api.

    Attributes:
        proto_version: Версия протокола ядра.
        core_version: Версия ПО ядра робота.
        api_version: Версия ПО rc10_api.
    """

    proto_version: str | int = 0x02000500
    core_version: str = '1.2.7'
    api_version: int = 3

    def get_full_version(self):
        return f'{self.core_version}.{self.proto_version}/{self.api_version}'


@dataclass
class RobotInfo:
    """
    Дата-класс с технической информацией о текущей модели робота и ПО.

    Attributes:
        robot_model: Имя модели робота
        client_version: Полная версия клиента.
    """

    robot_model: str = 'rc10b2'
    client_version: str = Version().get_full_version()
