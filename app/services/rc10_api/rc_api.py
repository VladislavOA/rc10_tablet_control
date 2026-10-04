import atexit
import sys
import threading
import time
from multiprocessing.pool import ThreadPool
from struct import pack

from rc10_api.source.ap_interface.controller_gravity import ControllerGravity
from rc10_api.source.ap_interface.controller_state import ControllerState
from rc10_api.source.ap_interface.io.io_host import IO
from rc10_api.source.ap_interface.motion.motion_host import Motion
from rc10_api.source.ap_interface.payload import PayLoad
from rc10_api.source.ap_interface.safety_status import SafetyStatus
from rc10_api.source.ap_interface.tool import Tool
from rc10_api.source.ap_interface.wrist.wrist_host import Wrist
from rc10_api.source.core.exceptions.connection_error import ServerPingError
from rc10_api.source.core.exceptions.data_validation_error.version_error import (
    ControllerUnlockError
)
from rc10_api.source.core.network.controller_socket import Controller
from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver
from rc10_api.source.features.logger import set_logger
from rc10_api.source.features.state_handler import StateHandler
from rc10_api.source.models.classes.data_classes.api_version import (
    RobotInfo, Version
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    ControllerUnlockCommand as Cun, Getters as Get, Setters as Set
)
from rc10_api.source.models.type_aliases import ExcInfoType


class RobotApi:
    # TODO: Future Feature: Add the separate thread and its logic for
    # controller socket command processing.
    # TODO: Migrate ControllerState, SafetyStatus and MotionMode classes to
    # separate state host subclass.
    # TODO: Add all states rt_data to SimpleJoystickUI (in Motion class) after
    # states classes migration.

    _controller: Controller | None
    _rtd_receiver: RTDReceiver | None
    _state_handler: StateHandler | None

    tool: Tool
    payload: PayLoad
    controller_state: ControllerState
    motion: Motion
    io: IO
    safety_status: SafetyStatus
    controller_gravity: ControllerGravity

    def __init__(
        self,
        ip: str,
        ignore_controller_exceptions: bool = False,
        read_only: bool = False,
        timeout: int = 5,
        **kwargs
    ) -> None:
        """
        Пользовательский клиент-класс rc10_api - входная точка управления роботом.

        Args:
            ip (str): IPv4 робота (без порта).
            ignore_controller_exceptions (bool): Флаг, позволяющий игнорировать
                ошибки обработчика состояний контроллера. При активации флага
                пользователям необходимо самостоятельно отслеживать состояние
                безопасности.
            read_only (bool): Флаг работы rc10_api в режиме read_only, подключение
                при этом происходит только к порту RTD.
            timeout (int): Таймаут на подключение к роботу (сек).
            Keyword Args:
                enable_logger (bool): Включить/выключить логирование
                    (в состоянии False последующие аргументы игнорируются).
                enable_logfile (bool): Включить/выключить логирование в файл.
                logger (logging.Logger): Пользовательский логгер
                    (переопределяет предустановленные настройки логгера).
                logfile_path (pathlib.Path): Путь для размещения файлов
                    логирования (по умолчанию создает папку рядом с исполняемым
                    файлом).
                logfile_name (pathlib.Path): Имя лог-файла (по умолчанию имя в
                    формате '__ДД.ММ.ГГГГ__ЧЧ.00__.log').
                logfile_level (int): Уровень логирования в файл.
                log_std_level (int): Уровень консольного логирования.
                show_std_traceback (bool): Включить/выключить полное
                    отображение ошибок в консоли.
        """
        self._read_only = read_only
        self._logger = set_logger(**kwargs)
        sys.excepthook = self._exit_program
        atexit.register(self._exit_program)
        self._is_sockets_active = True
        self._is_pool_active = True
        self._ip = ip
        self._ignore_controller_exceptions = ignore_controller_exceptions
        self._timeout = timeout
        self._thread_pool = ThreadPool(2)
        self._controller: Controller | None = None
        self._rtd_receiver: RTDReceiver | None = None
        self._state_handler: StateHandler | None = None
        self._start_flow(enable_state_handler=True)
        self.safety_status = SafetyStatus(self._rtd_receiver, self._logger)
        if not self._read_only:
            self.motion = Motion(
                self._controller, self._rtd_receiver, self._logger
            )
            self.tool = Tool(self._controller)
            self.payload = PayLoad(self._controller)
            self.controller_state = ControllerState(
                self._controller,
                self._rtd_receiver,
                self.motion.joint,
                self._logger
            )
            self.io = IO(self._controller, self._rtd_receiver, self._logger)
            self.controller_gravity = ControllerGravity(self._controller)
            self.wrist = Wrist(
                self._controller, self._rtd_receiver, self._logger
            )

    def _exit_program(self, exc_type=None, exc_value=None, exc_traceback=None):
        """
        Вызывается при любой ошибке главного потока и при завершении всей
        программы.

        Args:
            exc_type: Тип ошибки.
            exc_value: Значение ошибки.
            exc_traceback: Содержание ошибки и хвост.
        """

        if exc_type and exc_value and exc_traceback:
            if (
                issubclass(exc_type, KeyboardInterrupt)
                and len(exc_value.args) == 0
            ):
                exc_value.args = ('KeyboardInterrupt',)
            error = (exc_type, exc_value, exc_traceback)
        else:
            error = None
        self._shutdown_api_sockets(error)
        self._close_thread_pool()

    def _close_thread_pool(self):
        if (
            threading.current_thread() is threading.main_thread()
            and self._is_pool_active
        ):
            self._is_pool_active = False
            self._thread_pool.close()
            self._thread_pool.join()
            self._logger.debug(
                f'rc10_api private thread pool is closed (all threads are joined). '
                f'Threads is progress: {threading.active_count()}'
            )

    def _shutdown_api_sockets(self, exc_info: ExcInfoType = None):
        """
        Выходная точка rc10_api. Закрытие подключений, потоков.
        Работает в двух режимах. Если передается сообщение об ошибке, метод
        завершает работу rc10_api в аварийном режиме.

        Args:
            exc_info: ExcInfoType
        """

        if self._is_sockets_active:
            self._is_sockets_active = False
            if exc_info:
                if isinstance(exc_info, BaseException):
                    exc_info = (
                        type(exc_info), exc_info, exc_info.__traceback__
                    )
                elif not isinstance(exc_info, tuple):
                    exc_info = sys.exc_info()
                self._logger.exception(exc_info[1], exc_info=exc_info)
                self._logger.warning('rc10_api connection emergency shutdown')
            else:
                self._logger.info('rc10_api connection planned shutdown')
            if self._rtd_receiver:
                self._rtd_receiver.shutdown()
                self._logger.debug(
                    f'{self._rtd_receiver.__class__.__name__} socket shutdown'
                )
            if self._controller:
                self._controller.shutdown()
                self._logger.debug(
                    f'{self._controller.__class__.__name__} socket shutdown'
                )
            if self._state_handler:
                self._state_handler.shutdown()

    def _start_flow(self, enable_state_handler: bool):
        self._logger.info(f'Client version: [{RobotInfo.client_version}]')
        self._logger.info(f'Connecting to Robot at [{self._ip}]')
        self._rtd_receiver = self._initialise_rtd_receiver()
        if not self._read_only:
            self._controller = self._initialise_controller()
            if self._rtd_receiver and self._controller and self._ping_loop(5):
                self._validate_api_version()
                self._state_handler = (
                    self._initialise_state_handler()
                    if enable_state_handler else None
                )

    def _validate_api_version(self):
        if (server := self._get_server_version()) != RobotInfo.client_version:
            self._logger.warning(
                f'Client: [{RobotInfo.client_version}] != Server: [{server}]'
            )
        if not self._unlock_connection():
            raise ControllerUnlockError('Most probably server is busy')
        self._logger.info('Successfully authorized in Robot')

    def _initialise_controller(self) -> Controller:
        """
           Инициализация обертки для класса-контроллера робота.

           Returns:
               ControllerGateway: Объект обертки класса-контроллера.
           """
        controller = Controller(self._ip, self._timeout, self._logger)
        if controller.initialise():
            self._logger.debug(
                f'{controller.__class__.__name__} socket connected'
            )
        return controller

    def _initialise_rtd_receiver(self) -> RTDReceiver:
        """
        Инициализация фонового потока получения метрик робота 'rt_data'.
        С частотой 500 Гц обновляет поля дата-класса.

        Returns:
            RTDReceiver: Объект класса приема метрик робота.
        """

        rtd_receiver = RTDReceiver(self._ip, self._timeout)
        if rtd_receiver.initialise():
            self._logger.debug(
                f'{rtd_receiver.__class__.__name__} socket connected'
            )
            self._thread_pool.apply_async(
                rtd_receiver.receiving_loop,
                error_callback=self._shutdown_api_sockets
            )
        return rtd_receiver

    def _initialise_state_handler(self) -> StateHandler:
        """
        Инициализация фонового потока обработки состояний робота.
        Поток проверяет и логирует в 'DEBUG' режиме текущие состояния
        контроллера, безопасности и типа движения. При получении критического
        статуса поток закрывает исполнение программы в аварийном режиме.

        Returns:
            StateHandler: Объект класса обработчика состояний.
        """

        state_handler = StateHandler(
            self._rtd_receiver,
            self._logger,
            self._ignore_controller_exceptions
        )
        self._thread_pool.apply_async(
            state_handler.start,
            error_callback=self._shutdown_api_sockets
        )
        return state_handler

    def _unlock_connection(self) -> bool:
        self._controller.send(
            Cun.ctrlr_coms_unlock,
            pack('I', Version.proto_version)
        )
        response = self._controller.receive(Cun.ctrlr_coms_unlock, 'B')
        if not response or response[0] == 0:
            return False
        else:
            return True

    def _ping_loop(self, iterations: int) -> bool:
        """
        Пинг-команда. Высылается циклически.
        Нужна только для работы с реализацией серверной логики на момент
        написания (03.2024). Так как сервер не уведомляет пользователя об
        отказе на соединение, для корректного уведомления пользователя, после
        первичного (обычно успешного) подключения к сокету, высылается данная
        команда в течении некоторого времени. Эквивалентна команде получения
        версии RTD, за тем исключением, что оригинальная команда закроет сокет
        в случае ошибки, тогда как эта не перехватит ошибку.

        Args:
            iterations: Количество отправленных команд.

        Returns:
            bool:
                True — в случае корректно работающего соединения с сервером.
        """

        try:
            for _ in range(iterations):
                self._controller.send(Get.ctrlr_coms_get_proto_version)
                self._controller.receive(Get.ctrlr_coms_get_proto_version, 'I')
                time.sleep(0.1)
        except Exception as e:
            raise ServerPingError from e
        return True

    def _get_server_proto_version(self) -> int | None:
        """
        Получить версию 'rt_data' протокола робота.

        Returns:
            str: Версия 'rt_data' протокола.
        """

        self._controller.send(Get.ctrlr_coms_get_proto_version)
        response = self._controller.receive(
            Get.ctrlr_coms_get_proto_version, 'I'
        )
        return response[0] if response else None

    def _get_server_core_version(self) -> str:
        """
        Получить версию ядра контроллера робота.

        Returns:
            str: Версия ядра контроллера робота.
        """

        self._controller.send(Get.ctrlr_coms_get_sw_version)
        response = self._controller.receive(
            Get.ctrlr_coms_get_sw_version, '3I'
        )
        return (
            ''.join([str(item) + '.' for item in response])[:-1]
            if response else None
        )

    def _get_robot_model(self) -> str:
        """
        Получить название модели робота.

        Returns:
            str: Модель робота.
        """

        self._controller.send(Get.ctrlr_coms_get_robot_view_info)
        response = self._controller.receive(
            Get.ctrlr_coms_get_robot_view_info, '=L32c'
        )
        return (
            ''.join(
                [item.decode('utf-8')
                 if item != b'\x00' else '' for item in response[1:]]
            ) if response else None
        )

    def _get_server_version(self) -> str:
        return Version(
            core_version=self._get_server_core_version(),
            proto_version=self._get_server_proto_version()
        ).get_full_version()

    def get_robot_info(self) -> RobotInfo:
        """
        Поучить техническую информацию о модели робота и контроллера.

        Returns:
            RobotInfo: Дата-класс с технической информацией о текущей модели.
        """

        return RobotInfo(robot_model=self._get_robot_model())

    def save(self) -> bool:
        """
        Сохраняет пользовательские настройки для работы робота после его
        перезапуска.

        Returns:
            True: В случае успешной отправки команды.
        """

        return self._controller.send(Set.ctrlr_coms_store_settings)
