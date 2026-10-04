from __future__ import annotations

from struct import pack
from typing import TYPE_CHECKING

from rc10_api.source.core.exceptions.data_validation_error.generic_error import (
    WristStateError
)
from rc10_api.source.features.tools import sleep
from rc10_api.source.models.classes.data_classes.command_templates import (
    SetWristInputOutputTemplate
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Getters as Get
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Setters as Set
)
from rc10_api.source.models.constants import (
    AVAILABLE_WRIST_DIG_IN_INDEX_COUNT, AVAILABLE_WRIST_DIG_OUT_INDEX_COUNT,
    AVAILABLE_DIG_OUT_INDEX_COUNT, BITS_IN_BYTE, CHECK_FREQUENCY_SEC,
    CTRLR_IO_GET_FUNCTION_UNPACK_VALUES_TYPE,
    CTRLR_IO_SET_FUNCTION_PACK_FORMAT, CTRLR_WRIST_IO_SET_VALUE_PACK_FORMAT,
    DIGITAL_IO_INDEX_COUNT, NO_FUNC_ANSWER_VALUE, WRIST_DIGITAL_IO_INDEX_COUNT
)
from rc10_api.source.models.type_aliases import (
    DigitalIndex, DigitalWristIndex, WristInputActivationType_
)
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.tools import dataclass_to_tuple
from rc10_api.source.models.classes.enum_classes.io_functions import (
    InputFunction, OutputFunction
)
from rc10_api.source.models.type_aliases import InputFunction_, OutputFunction_
from rc10_api.source.models.classes.enum_classes.state_classes import (
    WristMode as Wm
)

if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver
    from rc10_api.source.core.network.controller_socket import Controller


validate_index = validation.validate_index
validate_literal = validation.validate_literal


class WristDigitalIO:
    _controller: Controller
    _rtd_receiver: RTDReceiver
    _logger: Logger

    def __init__(
        self, controller: Controller, rtd_receiver: RTDReceiver, logger: Logger
    ):

        self._controller = controller
        self._rtd_receiver = rtd_receiver
        self._logger = logger

    def _get_input(self, index: int, inputs_range: int) -> bool:
        """
        Получить текущее двоичное значение на 'index' цифровом входе.

        Args:
            index: Индекс входа.
        Returns:
            bool: True — есть сигнал, False — нет сигнала.
        """
        validate_index(index, inputs_range)
        mask = 1 << (index % BITS_IN_BYTE)
        return self._rtd_receiver.rt_data.wrist_dig_in & mask != 0

    def get_input(self, index: DigitalWristIndex) -> bool:
        """
        Получить текущее двоичное значение на 'index' цифровом входе платы
        запястья.

        Args:
            index: Индекс входа (0-1).
        Returns:
            bool: True — есть сигнал, False — нет сигнала.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not get input value, when wrist mode is {Wm.off}'
            )
        return self._get_input(
            index=index,
            inputs_range=range(AVAILABLE_WRIST_DIG_IN_INDEX_COUNT)
        )

    def get_output(self, index: DigitalWristIndex) -> bool:
        """
        Получить текущее двоичное значение на 'index' цифровом выходе платы
        запястья.

        Args:
            index: Индекс выхода (0-1).
        Returns:
            bool: True — есть сигнал, False — нет сигнала.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not get output value, when wrist mode is {Wm.off}'
            )
        validate_index(index, range(AVAILABLE_WRIST_DIG_OUT_INDEX_COUNT))
        mask = 1 << (index % BITS_IN_BYTE)
        return self._rtd_receiver.rt_data.wrist_dig_out & mask != 0

    def set_output(self, index: DigitalWristIndex, value: bool) -> bool:
        """
        Установить булево значение на определенный выход платы запястья.

        Args:
            index: Индекс выхода (0-1).
            value: True — есть сигнал, False — нет сигнала.
        Returns:
            True: В случае успешной отправки команды.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not set output value, when wrist mode is {Wm.off}'
            )
        validate_index(index, range(AVAILABLE_WRIST_DIG_OUT_INDEX_COUNT))
        set_output_template = SetWristInputOutputTemplate()
        dig_out_mask = set_output_template.dig_out_mask
        dig_out_mask = 1 << (index % BITS_IN_BYTE)
        set_output_template.dig_out_mask = dig_out_mask
        dig_out = set_output_template.dig_out
        dig_out = (1 if value else 0) << (index % BITS_IN_BYTE)
        set_output_template.dig_out = dig_out
        return self._controller.send(
            Set.ctrlr_coms_set_wrist_io,
            pack(
                CTRLR_WRIST_IO_SET_VALUE_PACK_FORMAT,
                *dataclass_to_tuple(set_output_template)
            )
        )

    def wait_any_input(self, await_sec: int = -1) -> bool:
        """
        Ожидать изменение двоичного сигнала на любом цифровом входе платы
        запястья.

        Args:
            await_sec: Лимит времени ожидания.
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                    условию).
        Returns:
            True: В случае изменения значения на одном или сразу на нескольких
                цифровых входах.
            False: В случае таймаута (если await_sec >= 0).
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not wait input value, when wrist mode is {Wm.off}'
            )
        current_inputs = self._rtd_receiver.rt_data.dig_in
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            if current_inputs != self._rtd_receiver.rt_data.dig_in:
                return True
        return False

    def wait_input(
        self, index: DigitalWristIndex, value: bool, await_sec: int = -1
    ) -> bool:
        """
        Ожидать изменение двоичного сигнала на 'index' цифровом входе платы
        запястья.

        Args:
            index: Индекс входа (0 — 1).
            value: Ожидаемый цифровой сигнал.
                True — есть сигнал.
                False — нет сигнала.
            await_sec: Лимит времени ожидания.
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                    условию).
        Returns:
            True: В случае получения ожидаемого сигнала.
            False: В случае таймаута (если await_sec >= 0).
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not wait input value, when wrist mode is {Wm.off}'
            )
        validate_index(index, range(AVAILABLE_WRIST_DIG_IN_INDEX_COUNT))
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            if self.get_input(index) == bool(value):
                return True
        return False

    def set_input_function(
        self, index: DigitalWristIndex, function: InputFunction_
    ) -> bool:
        """
        Устанавливает действие на 'index' цифровом входе платы запястья.

        Args:
            index: Индекс цифрового входа (0 — 1).
            function: Устанавливаемое действие на цифровом входе.
                'no_func' - отсутствие действия на цифровом входе.
                'move' - переход в состояние MOVE (начало движения по точкам)
                'hold' - переход в состояние HOLD (остановка робота и очистка
                    буфера точек).
                'pause' - переход в состояние PAUSE (остановка робота без
                    очистки буфера точек).
                'zero_gravity' - переход в состояние ZERO_GRAVITY (свободное
                    движение).
                'run' - переход в состояние RUN (включение робота).
                'move_to_home' - переход в домашнюю позицию.
        Returns:
            True: В случае успешной отправки команды.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not set input function, when wrist mode is {Wm.off}'
            )
        validate_literal('in_f', function)
        validate_index(index, range(AVAILABLE_WRIST_DIG_IN_INDEX_COUNT))
        return self._controller.send(
            Set.ctrlr_coms_set_wrist_dig_input_func.value,
            pack(
                CTRLR_IO_SET_FUNCTION_PACK_FORMAT,
                index,
                InputFunction[function].value
            )
        )

    def get_input_functions(
        self, index: DigitalWristIndex = None
    ) -> tuple[tuple[int, str], ...] | tuple[int, str]:
        """
        Получить установленное действие на 'index' цифровом входе платы
        запястья. При вызове без аргумента вернет все индексы цифровых входов и
        установленные на них действия.

        Args:
            index: Индекс цифрового входа (0-1).
        Returns:
            tuple: Индекс цифрового входа и установленное на нем действие:
                'no_func' - отсутствие действия на цифровом входе.
                'move' - переход в состояние MOVE (начало движения по точкам)
                'hold' - переход в состояние HOLD (остановка робота и очистка
                    буфера точек).
                'pause' - переход в состояние PAUSE (остановка робота без
                    очистки буфера точек).
                'zero_gravity' - переход в состояние ZERO_GRAVITY (свободное
                    движение).
                'run' - переход в состояние RUN (включение робота).
                'move_to_home' - переход в домашнюю позицию.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not get output function, when wrist mode is {Wm.off}'
            )
        self._controller.send(Get.ctrlr_coms_get_dig_input_func)
        response = self._controller.receive(
            Get.ctrlr_coms_get_dig_input_func,
            CTRLR_IO_GET_FUNCTION_UNPACK_VALUES_TYPE *
            (DIGITAL_IO_INDEX_COUNT + WRIST_DIGITAL_IO_INDEX_COUNT)
        )
        if index is None:
            result = []
            for index, value in enumerate(
                response[:AVAILABLE_WRIST_DIG_IN_INDEX_COUNT]
            ):
                result.append(
                    (index, InputFunction(value).name)
                )
            return result
        validate_index(index, range(AVAILABLE_WRIST_DIG_IN_INDEX_COUNT))
        return index, InputFunction(response[index]).name

    def set_active_output(
        self,
        wrist_index: DigitalWristIndex,
        output_index: DigitalIndex,
        activation_type: WristInputActivationType_,
    ):
        """
        Устанавливает активный сигнал на 'output_index' цифрового выхода
            контроллера по 'wrist_index' цифрового входа платы запястья.

        Args:
            wrist_index: Индекс цифрового входа платы запястья (0-1).
            output_index: Индекс цифрового выхода контроллера (0-23).
            activation_type: Тип активации цифрового выхода контроллера:
                'hold' - при удержании 'wrist_index' платы запястья
                'trigger' - при переключении 'wrist_index' платы запястья.
        Returns:
            True: В случае успешной отправки команды.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not set hold active function, '
                f'when wrist mode is {Wm.off}'
            )
        validate_index(wrist_index, range(AVAILABLE_WRIST_DIG_IN_INDEX_COUNT))
        validate_index(output_index, range(AVAILABLE_DIG_OUT_INDEX_COUNT))
        validate_literal('activation_type', activation_type)
        if activation_type == 'hold':
            function = InputFunction.ifunc_hold_io_dig_output
        elif activation_type == 'trigger':
            function = InputFunction.ifunc_trigger_io_dig_output
        return self._controller.send(
            Set.ctrlr_coms_set_wrist_dig_input_func,
            pack(
                CTRLR_IO_SET_FUNCTION_PACK_FORMAT,
                wrist_index,
                function + output_index
            )
        )

    def set_output_function(
            self,
            index: DigitalWristIndex,
            function: OutputFunction_
    ) -> bool:
        """
        Устанавливает действие на 'index' цифровом выходе платы запястья.

        Args:
            index: Индекс цифрового выхода (0 — 1).
            function: Устанавливаемое действие на цифровом выходе.
                'no_func' - отсутствие действия на цифровом выходе.
                'no_move_signal_false' - при остановленном роботе значение
                    устанавливается в 0.
                'no_move_signal_true' - при остановленном роботе значение
                    устанавливается в 1.
                'move_status_signal_true_false' - при остановленном роботе
                    значение устанавливается в 0, при движении - 1.
                'run_signal_true' - робот при состоянии RUN выдает 1.
                'warning_signal_true' - выдает при предупреждении 1 на цифровой
                    выход.
                'error_signal_true' - выдает при ошибке 1 на цифровой выход.

        Returns:
            True: В случае успешной отправки команды.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not set output function, when wrist mode is {Wm.off}'
            )
        validate_index(index, range(AVAILABLE_WRIST_DIG_OUT_INDEX_COUNT))
        validate_literal('out_f', function)
        return self._controller.send(
            Set.ctrlr_coms_set_wrist_dig_output_func.value,
            pack(
                CTRLR_IO_SET_FUNCTION_PACK_FORMAT,
                index,
                OutputFunction[function].value,
            )
        )

    def get_output_functions(
            self, index: DigitalWristIndex = None
    ) -> tuple[tuple[int, str], ...] | tuple[int, str]:
        """
        Получить установленное действие на 'index' цифровом выходе платы
        запястья. При вызове без аргумента вернет все активные индексы цифровых
        выходов и установленные на них действия.

        Args:
            index: Индекс выхода (0-1).
        Returns:
            tuple: Индекс и установленное на нем действие
                'no_func' - отсутствие действия на цифровом выходе.
                'no_move_signal_false' - при остановленном роботе значение
                    устанавливается в 0.
                'no_move_signal_true' - при остановленном роботе значение
                    устанавливается в 1.
                'move_status_signal_true_false' - при остановленном роботе
                    значение устанавливается в 0, при движении - 1.
                'run_signal_true' - робот при состоянии RUN выдает 1.
                'warning_signal_true' - выдает при предупреждении 1 на цифровой
                    выход.
                'error_signal_true' - выдает при ошибке 1 на цифровой выход.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not get output function, when wrist mode is {Wm.off}'
            )
        self._controller.send(Get.ctrlr_coms_get_dig_output_func)
        response = self._controller.receive(
            Get.ctrlr_coms_get_dig_output_func,
            CTRLR_IO_GET_FUNCTION_UNPACK_VALUES_TYPE *
            (DIGITAL_IO_INDEX_COUNT + WRIST_DIGITAL_IO_INDEX_COUNT)
        )
        if index is None:
            result = []
            for index, value in enumerate(
                response[:AVAILABLE_WRIST_DIG_OUT_INDEX_COUNT]
            ):
                if value != NO_FUNC_ANSWER_VALUE:
                    result.append(
                        (index, OutputFunction(value).name)
                    )
            return tuple(result)
        validate_index(index, range(AVAILABLE_WRIST_DIG_OUT_INDEX_COUNT))
        return index, OutputFunction(response[index]).name
