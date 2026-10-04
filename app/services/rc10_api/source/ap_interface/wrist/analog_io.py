from __future__ import annotations
from struct import pack
from typing import TYPE_CHECKING

from rc10_api.source.core.exceptions.data_validation_error.generic_error import (
    WristAIOUnitsNotSet,
    WristStateError
)
from rc10_api.source.features.tools import sleep
from rc10_api.source.models.classes.data_classes.command_templates import (
    SetWristInputOutputTemplate,
)
from rc10_api.source.models.classes.enum_classes.controller_commands import (
    Setters as Set
)
from rc10_api.source.models.classes.enum_classes.various_types import PowerUnitsCode
from rc10_api.source.models.constants import (
    AMPERAGE_VALUES_RANGE,
    CHECK_FREQUENCY_SEC,
    AVAILABLE_WRIST_AN_IN_INDEX_COUNT,
    CTRLR_WRIST_IO_SET_VALUE_PACK_FORMAT,
    SET_WRIST_MODE_AWAIT_SEC,
    VOLTAGE_INPUT_INDEXES_RANGE,
    VOLTAGE_VALUES_RANGE,
)
from rc10_api.source.models.type_aliases import (
    AnalogIndex, CompareSigns, PowerUnits
)
from rc10_api.source.models.classes.enum_classes.state_classes import (
    WristMode as Wm
)
from rc10_api.source.core.exceptions.data_validation_error.argument_error import (
    validation
)
from rc10_api.source.features.tools import dataclass_to_tuple

if TYPE_CHECKING:
    from logging import Logger

    from rc10_api.source.core.network.rtd_receiver_socket import RTDReceiver
    from rc10_api.source.core.network.controller_socket import Controller


validate_index = validation.validate_index
validate_literal = validation.validate_literal
validate_value = validation.validate_value


class WristAnalogIO:
    _controller: Controller
    _rtd_receiver: RTDReceiver
    _logger: Logger

    def __init__(
        self, controller: Controller, rtd_receiver: RTDReceiver, logger: Logger
    ):
        self._controller = controller
        self._rtd_receiver = rtd_receiver
        self._logger = logger

    def check_wrist_enable(self) -> bool:
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError()
        return True

    def get_input(
        self, index: AnalogIndex, units: PowerUnits
    ) -> tuple[int, float]:
        """
        Получить текущее значение силы тока / напряжения на 'index' аналоговом
        входе платы запястья.

        Args:
            index: Индекс входа (0-1).
            units: Единицы измерения. 'mA' - сила тока. 'V' - напряжение.
        Returns:
            tuple: Индекс входа и его значение.
        """
        if self.check_wrist_enable():
            if self._set_input_units(index, units):
                return (
                    index, self._rtd_receiver.rt_data.wrist_an_in_value[index]
                )
            else:
                raise WristAIOUnitsNotSet()

    def _set_input_units(
        self,
        index: AnalogIndex,
        units: PowerUnits,
        await_sec: int = SET_WRIST_MODE_AWAIT_SEC
    ) -> bool:
        """
        Установить единицы измерения, снимаемые на 'index' аналоговом входе
        платы запястья. Тип устанавливаемого значения зависит от переменной
        units.

        Args:
            index: Индекс выхода (0-1).
            units: Единицы измерения. 'mA' - сила тока. 'V' - напряжение.
        Returns:
            True: В случае успешной отправки команды.
            False: В случае таймаута или неудачной отправки команды.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not set input units, when wrist mode is {Wm.off}'
            )
        validate_literal('power', units)
        validate_index(index, range(AVAILABLE_WRIST_AN_IN_INDEX_COUNT))
        set_input_output_template = SetWristInputOutputTemplate()
        set_input_output_template.an_in_mask[index] = 1
        set_input_output_template.an_in_mode[index] = PowerUnitsCode[units]
        set_input_output_template.mux_mode = Wm.analog_in
        res = self._controller.send(
            Set.ctrlr_coms_set_wrist_io,
            pack(
                CTRLR_WRIST_IO_SET_VALUE_PACK_FORMAT,
                *dataclass_to_tuple(set_input_output_template),
            ),
        )
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            if (
                self._rtd_receiver.rt_data.wrist_an_in_curr_mode[index]
                == PowerUnitsCode[units]
            ):
                return res
        return False

    def wait_input(
        self,
        index: AnalogIndex,
        threshold_value: float,
        units: PowerUnits,
        greater_or_less: CompareSigns,
        await_sec: int = -1,
    ) -> bool:
        """
        Ожидать преодоление порогового значения на 'index' аналоговом входе
        платы запястья.

        Args:
            index: Индекс входа (0-1).
            threshold_value: Пороговое значение силы тока (4 — 20 мА)
                напряжения (0 — 10 В).
            greater_or_less: Устанавливает тип ожидания.
                '>' — ждать преодоления высокого порогового значения.
                '<' — ждать преодоления низкого порогового значения.
            await_sec: Лимит времени ожидания.
                -1 — безлимитное ожидание.
                0 — одна итерация цикла ожидания (эквивалентно разовому
                    условию).
        Returns:
            True: В случае преодоления порогового значения.
            False: В случае таймаута (если await_sec >= 0).
        Raises:
            ArgIndexError: При некорректно указанном индексе.
            ArgComparisonError: При некорректно указанном знаке сравнения.
        """
        if self._rtd_receiver.rt_data.wrist_mode == Wm.off:
            raise WristStateError(
                f'Can not wait input value, when wrist mode is {Wm.off}'
            )
        validate_literal('power', units)
        validate_index(index, range(AVAILABLE_WRIST_AN_IN_INDEX_COUNT))
        validate_value(
            threshold_value,
            (
                VOLTAGE_VALUES_RANGE
                if index in range(VOLTAGE_INPUT_INDEXES_RANGE)
                else AMPERAGE_VALUES_RANGE
            ),
        )
        validate_literal('compare', greater_or_less)
        self._logger.info(f'Waiting analog signal on {index} wrist input...')
        for _ in sleep(await_sec=await_sec, frequency=CHECK_FREQUENCY_SEC):
            match greater_or_less:
                case '<':
                    if self.get_input(index, units)[1] <= threshold_value:
                        self._logger.info(
                            (
                                f'Analog signal on wrist {index}: '
                                f'{self.get_input(index, units)[1]} < '
                                f'{threshold_value}'
                            )
                        )
                        return True
                case '>':
                    if self.get_input(index, units)[1] >= threshold_value:
                        self._logger.info(
                            (
                                f'Analog signal on wrist {index}: '
                                f'{self.get_input(index, units)[1]} > '
                                f'{threshold_value}'
                            )
                        )
                        return True
        self._logger.info(f'Analog signal on {index} wrist input timeout')
        return False
